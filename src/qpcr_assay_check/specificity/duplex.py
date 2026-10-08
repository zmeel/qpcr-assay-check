"""Estimate the stability of an oligo bound to a mismatched site.

The estimate uses primer3's nearest-neighbour model for the oligo against the reverse complement of
the subject bases it is aligned to. It is an *estimate of duplex stability only*: a mismatch at the
3'-terminal base is treated as an unpaired overhang, so it hardly changes the melting temperature
even though it usually prevents extension. Priming is therefore judged from the mismatch and
3'-end columns, never from Tm.

Degenerate codes are resolved on both sides before anything is computed, because primer3 cannot
pair one: left in, a Y opposite an R is no pair at all.

- The **oligo**: against the template, since the mix holds every member and the best-binding one
  primes. Left in, the perfect-match baseline came out about 15 C too low and the ΔTm of a site
  depended on which member the template happened to take (user, 2026-10-07, from two influenza
  rows that differed in nothing else).
- The **template**: an ambiguity code in the genome takes the base that pairs with the oligo
  where the two are compatible, which is how R6 grades such a position - a match. Left in, a
  single N read as a 13 C drop and could trip the "Tm <= annealing" flag on a site graded a
  match (code review, 2026-10-08).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from ..align import realign
from ..oligo import iupac, thermo

log = logging.getLogger(__name__)


#: Degenerate oligos are resolved against the template first, so only the positions the template
#: contradicts are ever expanded; this caps that expansion (2^6) in case a site is unusual.
MAX_RESOLVED = 64


def resolved_oligos(oligo: str, q_aln: str | None, s_aln: str) -> list[str]:
    """The oligo as the mix's best-binding members for this template, degenerate codes removed.

    Each degenerate position takes the template's base where the two are compatible - that member
    of the mix binds there - and is expanded where the template contradicts it, so the caller can
    take the member that binds best. Returns ``[oligo]`` unchanged when the alignment does not
    describe the whole oligo (a partial site) or the expansion would be too large.
    """
    if not iupac.is_degenerate(oligo):
        return [oligo]
    if q_aln is None:
        return [oligo]
    picked: list[str] = []
    for qc, sc in zip(q_aln, s_aln, strict=False):
        if qc == "-":
            continue
        picked.append(sc if qc not in "ACGT" and sc in "ACGT" and iupac.compatible(qc, sc) else qc)
    candidate = "".join(picked)
    if len(candidate) != len(oligo):
        return [oligo]  # a partial or odd alignment: leave it as it was
    try:
        return iupac.expand(candidate, MAX_RESOLVED)
    except Exception:  # noqa: BLE001 - over the cap: no estimate is better than a wrong baseline
        return [oligo]


def resolved_template(q_aln: str | None, s_aln: str) -> str:
    """``s_aln`` with every ambiguity code in the template replaced by one concrete base.

    A code compatible with the oligo's base there takes that base: the position is a match, which
    is what R6 grades it, and primer3 can pair it. One the oligo contradicts takes the first of
    its own bases, so the position is a defined mismatch rather than a character that pairs with
    nothing, and so does one with no oligo base opposite it (a gap in the oligo: a base inserted
    in the template). Gaps and unaligned positions in the template are left alone.
    """
    if q_aln is None:
        return s_aln
    out: list[str] = []
    for qc, sc in zip(q_aln, s_aln, strict=False):
        if sc in "ACGT-." or sc not in iupac.IUPAC_CODES:
            out.append(sc)
            continue
        members = sorted(iupac.IUPAC_CODES[sc])
        if qc not in iupac.IUPAC_CODES:  # a gap or an unaligned column opposite the code
            out.append(members[0])
            continue
        out.append(next((b for b in members if iupac.compatible(qc, b)), members[0]))
    return "".join(out) + s_aln[len(out) :]


def estimate_duplex(
    oligo: str, s_aln: str, cond: thermo.Conditions, nM: float, q_aln: str | None = None
) -> tuple[float | None, float | None, float | None]:
    """Return ``(tm_c, dg_kcal, delta_tm_c)``; ``tm_c`` is None if no duplex is predicted.

    ``q_aln``, the oligo as aligned, resolves the degenerate codes on both sides against each
    other (see the module docstring); without it both are used as written, as before.
    """
    s_aln = resolved_template(q_aln, s_aln)
    subject = realign.sanitise_subject(s_aln.replace("-", "").replace(".", ""))
    if len(subject) < 8:
        return None, None, None
    template = iupac.reverse_complement(subject)
    best: tuple[Any, Any] | None = None
    for member in resolved_oligos(oligo, q_aln, s_aln):
        try:
            actual = thermo.heterodimer(member, template, cond, nM=nM)
            if not actual.found or actual.tm_c is None:
                continue
            if best is not None and actual.tm_c <= best[0].tm_c:
                continue  # the member that binds best is the one that primes
            perfect = thermo.heterodimer(member, iupac.reverse_complement(member), cond, nM=nM)
        except Exception as exc:  # noqa: BLE001 - primer3 raises plain exceptions on odd input
            log.debug("duplex estimate failed for %s: %s", member, exc)
            continue
        best = (actual, perfect)
    if best is None:
        return None, None, None
    actual, perfect = best
    delta = actual.tm_c - perfect.tm_c if perfect.found and perfect.tm_c is not None else None
    return actual.tm_c, actual.dg_kcal, delta


def site_duplex(
    reaction: Any,
) -> Callable[[Any], tuple[float | None, float | None, float | None]]:
    """A duplex estimate per site under the reaction conditions (``cfg.reaction``), cached by
    oligo and aligned template: thousands of genomes share few distinct site variants."""
    cond = thermo.Conditions.from_reaction(reaction)
    memo: dict[tuple[str, str, str, bool], tuple[float | None, float | None, float | None]] = {}

    def estimate(site: Any) -> tuple[float | None, float | None, float | None]:
        if site.source == "blast_partial_worst_case":
            return None, None, None  # unobserved bases: no estimate
        probe = site.role == "probe"
        key = (site.oligo, site.q_aln, site.s_aln, probe)
        if key not in memo:
            nM = reaction.probe_nM if probe else reaction.primer_nM
            memo[key] = estimate_duplex(site.oligo, site.s_aln, cond, nM, site.q_aln)
        return memo[key]

    return estimate
