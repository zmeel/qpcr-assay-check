"""Turn BLAST alignments into full-length binding sites and classify them.

Three sources, from most to least certain:

``blast_full``
    BLAST's own alignment already covers the whole oligo, so its alignment strings give the exact
    mismatches; nothing needs to be fetched.
``realigned``
    BLAST stopped early (a partial hit); the subject window around it was fetched and the whole
    oligo was re-aligned semi-globally.
``blast_partial_worst_case``
    A partial hit that was not re-aligned (it cannot possibly reach a relevant level, or the
    window could not be fetched). The unaligned bases are assumed to match as well as BLAST's
    scoring allows, which is the *risk-conservative* assumption for an assay: with match +1 and
    mismatch -3, an alignment that stops early implies at least one mismatch per four unaligned
    bases (extending through a run with fewer would have raised the score).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Literal

from ..align import realign
from ..config import SiteCriteria, SiteRules
from ..ncbi.parser import Hit, HitDescription, Hsp
from ..oligo import iupac
from .models import Level, SiteResult

RecordType = Literal["genomic", "transcript", "other"]

_TRANSCRIPT_PREFIXES = ("NM_", "XM_", "NR_", "XR_")
_GENOMIC_PREFIXES = ("NC_", "NG_", "NT_", "NW_", "AC_")
_GENOMIC_WORDS = re.compile(
    r"chromosome|genomic|contig|scaffold|clone|whole genome|assembly|RefSeqGene", re.I
)
_TRANSCRIPT_WORDS = re.compile(r"mRNA|cDNA|transcript", re.I)


def record_type(accession: str, title: str) -> RecordType:
    """Best-effort classification of a subject record from its accession prefix and title."""
    if accession.startswith(_TRANSCRIPT_PREFIXES):
        return "transcript"
    if accession.startswith(_GENOMIC_PREFIXES) or _GENOMIC_WORDS.search(title):
        return "genomic"
    if _TRANSCRIPT_WORDS.search(title):
        return "transcript"
    return "other"


def role_of(label: str) -> str:
    """``forward_v2`` -> ``forward``."""
    return label.split("_v")[0]


def _quarter(n: int) -> int:
    return math.ceil(n / 4) if n > 0 else 0


@dataclass
class Candidate:
    """A BLAST alignment (HSP) of one oligo to one subject, before full-length assessment."""

    tier: str
    label: str
    role: str
    oligo: str
    hit: Hit
    desc: HitDescription | None
    hsp: Hsp
    metrics: realign.Metrics
    u5: int
    u3: int

    @property
    def qlen(self) -> int:
        """Length of the oligo."""
        return len(self.oligo)

    @property
    def partial(self) -> bool:
        """True if BLAST left oligo bases unaligned."""
        return self.u5 > 0 or self.u3 > 0

    @property
    def orientation(self) -> Literal["+", "-"]:
        """'+' if the oligo equals the subject's forward strand, '-' if its reverse complement."""
        return "+" if self.hsp.hit_strand == "Plus" else "-"

    @property
    def lower_bound(self) -> int:
        """Fewest mismatches plus gaps the full-length alignment can have."""
        m = self.metrics
        return m.n_mismatch + m.n_gap + _quarter(self.u5) + _quarter(self.u3)

    @property
    def accession(self) -> str:
        """``accession.version`` of the primary subject record."""
        return (self.desc.accession_version if self.desc else None) or "unknown"


def make_candidate(tier: str, label: str, oligo: str, hit: Hit, hsp: Hsp) -> Candidate:
    """Wrap an HSP; measures its aligned part and how much of the oligo BLAST left out."""
    if not hsp.qseq or not hsp.hseq:
        raise ValueError("BLAST report without alignment strings; cannot assess the hit")
    return Candidate(
        tier=tier,
        label=label,
        role=role_of(label),
        oligo=oligo,
        hit=hit,
        desc=hit.descriptions[0] if hit.descriptions else None,
        hsp=hsp,
        metrics=realign.measure(hsp.qseq, hsp.hseq),
        u5=hsp.query_from - 1,
        u3=len(oligo) - hsp.query_to,
    )


def _metrics(
    length: int, defects: set[int], n_match: int, n_mismatch: int, n_gap: int, n_amb: int
) -> realign.Metrics:
    clean = 0
    for p in range(length, 0, -1):
        if p in defects:
            break
        clean += 1
    return realign.Metrics(
        oligo_length=length,
        n_match=n_match,
        n_mismatch=n_mismatch,
        n_gap=n_gap,
        n_ambiguous=n_amb,
        defect_positions=tuple(sorted(defects)),
        clean_3prime_nt=clean,
        mismatches_last5=sum(p > length - 5 for p in defects),
        mismatches_last3=sum(p > length - 3 for p in defects),
        terminal_defect=length in defects,
    )


def meets(m: realign.Metrics, c: SiteCriteria) -> bool:
    """Does an alignment satisfy one set of limits?"""
    return (
        m.n_mismatch <= c.max_mismatches
        and m.n_gap <= c.max_gaps
        and m.clean_3prime_nt >= c.min_clean_3prime_nt
    )


def classify(m: realign.Metrics, rules: SiteRules) -> Level:
    """critical / warning / minor according to the configured limits."""
    if meets(m, rules.critical):
        return "critical"
    if meets(m, rules.warning):
        return "warning"
    return "minor"


def can_reach_warning(c: Candidate, rules: SiteRules) -> bool:
    """False if even the most favourable full-length alignment would stay 'minor'.

    Two consequences of BLAST reporting a locally maximal alignment (an assumption that the
    validation script in scripts/ checks against real hits):

    * the mismatch bound described in the module docstring, and
    * the first base beyond the alignment is a mismatch (a matching base would have raised the
      score, so it would have been included). At the 3' end this caps the run of clean 3'
      nucleotides at ``u3 - 1``.
    """
    if c.lower_bound > rules.warning.max_mismatches:
        return False
    return not (c.u3 > 0 and c.u3 - 1 < rules.warning.min_clean_3prime_nt)


def footprint(c: Candidate) -> tuple[int, int]:
    """Expected span of the whole oligo on the subject, in forward-strand coordinates."""
    h = c.hsp
    if c.orientation == "+":
        return h.hit_from - c.u5, h.hit_to + c.u3
    return h.hit_to - c.u3, h.hit_from + c.u5


def window_for(c: Candidate, pad: int, subject_length: int | None) -> tuple[int, int]:
    """Forward-strand window to fetch: the expected footprint plus ``pad`` on each side."""
    lo, hi = footprint(c)
    lo = max(1, lo - pad)
    hi = hi + pad
    if subject_length:
        hi = min(subject_length, hi)
    return lo, hi


def _common(c: Candidate) -> dict[str, object]:
    d = c.desc
    return {
        "tier": c.tier,
        "query": c.label,
        "role": c.role,
        "oligo": c.oligo,
        "accession": c.accession,
        "taxid": d.taxid if d else None,
        "organism": d.sciname if d else None,
        "title": (d.title if d else "")[:200],
        "n_merged": len(c.hit.descriptions),
        "orientation": c.orientation,
    }


def _result(
    c: Candidate,
    *,
    source: str,
    start: int,
    end: int,
    q_aln: str,
    s_aln: str,
    mid: str,
    m: realign.Metrics,
    n_unaligned: int,
    rules: SiteRules,
    site_id: str,
) -> SiteResult:
    return SiteResult(
        id=site_id,
        **_common(c),  # type: ignore[arg-type]
        subject_start=start,
        subject_end=end,
        source=source,  # type: ignore[arg-type]
        q_aln=q_aln,
        s_aln=s_aln,
        midline=mid,
        n_match=m.n_match,
        n_mismatch=m.n_mismatch,
        n_gap=m.n_gap,
        n_ambiguous=m.n_ambiguous,
        n_unaligned=n_unaligned,
        defect_positions=list(m.defect_positions),
        mismatches_last5=m.mismatches_last5,
        mismatches_last3=m.mismatches_last3,
        terminal_defect=m.terminal_defect,
        clean_3prime_nt=m.clean_3prime_nt,
        level=classify(m, rules),
    )


def site_from_full(c: Candidate, rules: SiteRules, site_id: str) -> SiteResult:
    """A hit whose BLAST alignment already spans the whole oligo."""
    h = c.hsp
    assert h.qseq and h.hseq
    return _result(
        c,
        source="blast_full",
        start=min(h.hit_from, h.hit_to),
        end=max(h.hit_from, h.hit_to),
        q_aln=h.qseq,
        s_aln=h.hseq,
        mid=realign.midline(h.qseq, h.hseq),
        m=c.metrics,
        n_unaligned=0,
        rules=rules,
        site_id=site_id,
    )


def site_from_bound(c: Candidate, rules: SiteRules, site_id: str) -> SiteResult:
    """A partial hit that was not re-aligned: assume the unaligned bases fit as well as possible."""
    m, h = c.metrics, c.hsp
    assert h.qseq and h.hseq
    n5, n3 = _quarter(c.u5), _quarter(c.u3)
    defects = {p + c.u5 for p in m.defect_positions}
    defects |= set(range(1, n5 + 1))
    defects |= set(range(c.qlen - c.u3 + 1, c.qlen - c.u3 + n3 + 1))  # innermost 3' flank bases
    est = _metrics(
        c.qlen,
        defects,
        n_match=m.n_match + (c.u5 - n5) + (c.u3 - n3),
        n_mismatch=m.n_mismatch + n5 + n3,
        n_gap=m.n_gap,
        n_amb=m.n_ambiguous,
    )
    lo, hi = footprint(c)
    return _result(
        c,
        source="blast_partial_worst_case",
        start=lo,
        end=hi,
        q_aln=c.oligo,
        s_aln="." * c.u5 + h.hseq + "." * c.u3,
        mid=" " * c.u5 + realign.midline(h.qseq, h.hseq) + " " * c.u3,
        m=est,
        n_unaligned=c.u5 + c.u3,
        rules=rules,
        site_id=site_id,
    )


def site_from_alignment(
    c: Candidate,
    aln: realign.Alignment,
    window: str,
    w_lo: int,
    rules: SiteRules,
    site_id: str,
) -> SiteResult:
    """A partial hit completed by re-aligning the whole oligo inside the fetched window."""
    m = realign.measure(aln.q_aln, aln.s_aln)
    if c.orientation == "+":
        start, end = w_lo + aln.s_start, w_lo + aln.s_end - 1
    else:  # the window was reverse-complemented: index i corresponds to w_hi - i
        w_hi = w_lo + len(window) - 1
        start, end = w_hi - (aln.s_end - 1), w_hi - aln.s_start
    return _result(
        c,
        source="realigned",
        start=start,
        end=end,
        q_aln=aln.q_aln,
        s_aln=aln.s_aln,
        mid=realign.midline(aln.q_aln, aln.s_aln),
        m=m,
        n_unaligned=0,
        rules=rules,
        site_id=site_id,
    )


def oriented_window(window: str, orientation: str) -> str:
    """The fetched forward-strand window, read in the oligo's orientation."""
    clean = realign.sanitise_subject(window)
    return clean if orientation == "+" else iupac.reverse_complement(clean)
