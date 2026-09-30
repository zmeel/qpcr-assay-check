"""Partner scan: find the partner primer and the probe next to an off-target primer site.

BLAST reports a site only when its alignment scores above the E-value cut-off (see
:mod:`.reach`): a 17-nt primer with two internal mismatches can go unreported although it may
still prime. A product needs *two* primer sites, so once BLAST has reported one of them the other
need not come from BLAST: the sequence a product could span (``max_amplicon_size``, in the
direction the primer extends) is fetched and every oligo of the partner role is aligned in it
end to end. Inside every predicted off-target product without a reported probe site, each probe
is re-aligned the same way. Only sites of at least warning level are added. Every fetch (partner
windows first, then products) counts against ``specificity.partner_scan_max_windows``. The scan
does not find a pair of which BLAST reported neither primer.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field, replace
from typing import Literal

from ..align import realign
from ..config import SpecificitySettings
from ..models import Assay
from .fetch import WindowFetcher
from .models import AmpliconResult, PartnerScan, SiteResult
from .sites import oriented_window, site_from_scan

log = logging.getLogger(__name__)

_LEVEL_RANK = {"critical": 0, "warning": 1, "minor": 2}


def facing_window(site: SiteResult, max_size: int) -> tuple[int, int]:
    """Forward-strand span a product primed at ``site`` could cover (at most ``max_size``)."""
    if site.orientation == "+":
        lo, hi = site.subject_start, site.subject_start + max_size - 1
    else:
        lo, hi = max(1, site.subject_end - max_size + 1), site.subject_end
    if site.subject_length:
        hi = min(hi, site.subject_length)
    return lo, hi


class _Known:
    """Sites already known, indexed by tier, record, oligo and strand: a scanned site that
    overlaps one of them is not new (tiers are kept apart, as products are paired per tier)."""

    def __init__(self, sites: list[SiteResult]) -> None:
        self._by: dict[tuple[str, str, str, str], list[tuple[int, int]]] = {}
        for s in sites:
            self.add(s)

    @staticmethod
    def _key(s: SiteResult) -> tuple[str, str, str, str]:
        return s.tier, s.accession, s.query, s.orientation

    def add(self, s: SiteResult) -> None:
        self._by.setdefault(self._key(s), []).append((s.subject_start, s.subject_end))

    def overlaps(self, s: SiteResult) -> bool:
        return any(
            lo <= s.subject_end and s.subject_start <= hi
            for lo, hi in self._by.get(self._key(s), ())
        )


def _faces(anchor: SiteResult, other: SiteResult) -> bool:
    """Would the two sites form a product (the '+' site first, the '-' site last)?"""
    left, right = (anchor, other) if anchor.orientation == "+" else (other, anchor)
    return left.subject_start < right.subject_start and left.subject_end < right.subject_end


@dataclass
class ScanState:
    """Windows fetched by the scan (by anchor site id) and what it found."""

    windows: dict[str, tuple[int, str]] = field(default_factory=dict)
    summary: PartnerScan = field(default_factory=lambda: PartnerScan(primer_sites=0, windows=0))


class PartnerScanner:
    """Runs the scan for one specificity assessment."""

    def __init__(
        self,
        assay: Assay,
        queries: dict[str, str],
        rules: SpecificitySettings,
        scoring: realign.Scoring,
        fetcher: WindowFetcher,
        ids: Iterator[int],
    ) -> None:
        self.assay = assay
        self.queries = queries
        self.rules = rules
        # an unknown template base is no evidence of binding: score it as a mismatch
        self.scoring = replace(scoring, unobserved_matches=False)
        self.fetcher = fetcher
        self.ids = ids
        self.state = ScanState()

    def _labels(self, role: str) -> list[str]:
        return [lb for lb in self.queries if self.assay.role_of(lb) == role]

    def _best(
        self,
        label: str,
        window: str,
        w_lo: int,
        orientations: tuple[Literal["+", "-"], ...],
        anchor: SiteResult,
        role: str,
        note: str,
        accept: Callable[[SiteResult], bool] = lambda s: True,
    ) -> SiteResult | None:
        """The best acceptable end-to-end alignment of one oligo in the window."""
        site_rules = self.rules.probe_site if role == "probe" else self.rules.primer_site
        best: SiteResult | None = None
        for o in orientations:
            aln = realign.align_semiglobal(
                self.queries[label], oriented_window(window, o), self.scoring
            )
            s = site_from_scan(
                anchor, label=label, role=role, oligo=self.queries[label], orientation=o,
                aln=aln, w_lo=w_lo, w_len=len(window), rules=site_rules, site_id="S0", note=note,
            )  # fmt: skip
            if not accept(s):
                continue
            key = (_LEVEL_RANK[s.level], s.n_mismatch + s.n_gap)
            if best is None or key < (_LEVEL_RANK[best.level], best.n_mismatch + best.n_gap):
                best = s
        return best

    def _fetches_left(self) -> int:
        s = self.state.summary
        return self.rules.partner_scan_max_windows - s.windows - s.product_windows

    def partners(self, sites: list[SiteResult], anchors: list[SiteResult]) -> list[SiteResult]:
        """Scan next to each anchor (priming primer sites of the off-target tiers) for partner
        primers; returns the new sites that can prime and face their anchor."""
        ordered = sorted(anchors, key=lambda s: (_LEVEL_RANK[s.level], int(s.id[1:])))
        summary = self.state.summary
        summary.primer_sites = len(ordered)
        known = _Known(sites)
        added: list[SiteResult] = []
        for n, anchor in enumerate(ordered, start=1):
            if anchor.accession == "unknown":
                summary.no_accession += 1
                continue
            if self._fetches_left() <= 0:
                summary.not_scanned += 1
                continue
            lo, hi = facing_window(anchor, self.rules.max_amplicon_size)
            before = self.fetcher.n_failed
            window = self.fetcher.get(anchor.accession, lo, hi)
            summary.windows += 1
            if window is None:
                summary.windows_failed += self.fetcher.n_failed - before or 1
                continue
            self.state.windows[anchor.id] = (lo, window)
            # the partner lies beyond the anchor's first base: aligning only there keeps the
            # anchor's own site from being the best alignment and hiding a real partner
            if anchor.orientation == "+":
                part, p_lo = window[1:], lo + 1
            else:
                part, p_lo = window[:-1], lo
            if not part:
                continue
            partner_role = "reverse" if anchor.role == "forward" else "forward"
            facing: Literal["+", "-"] = "-" if anchor.orientation == "+" else "+"
            note = f"found by the partner scan next to {anchor.id}; not reported by BLAST"
            for label in self._labels(partner_role):
                s = self._best(
                    label, part, p_lo, (facing,), anchor, partner_role, note,
                    accept=lambda s, a=anchor: s.level != "minor" and _faces(a, s),
                )  # fmt: skip
                if s is None or known.overlaps(s):
                    continue
                s.id = f"S{next(self.ids)}"
                known.add(s)
                added.append(s)
            if n % 200 == 0:
                log.info("  partner scan: %d / %d primer sites", n, len(ordered))
        summary.primer_sites_added = len(added)
        return added

    def _product(self, a: AmpliconResult) -> str | None:
        """The product's forward-strand sequence: from a scan window when one holds it, else
        fetched (counted as a product window)."""
        for i in (a.left_site, a.right_site):
            if i in self.state.windows:
                lo, window = self.state.windows[i]
                seq = window[a.start - lo : a.end - lo + 1]
                if len(seq) == a.length:
                    return seq
        summary = self.state.summary
        if self._fetches_left() <= 0:
            summary.products_not_scanned += 1
            return None
        before = self.fetcher.n_failed
        seq = self.fetcher.get(a.accession, a.start, a.end)
        summary.product_windows += 1
        if seq is None or len(seq) != a.length:
            summary.product_windows_failed += self.fetcher.n_failed - before or 1
            return None
        return seq

    def probes(self, amplicons: list[AmpliconResult], sites: list[SiteResult]) -> list[SiteResult]:
        """Re-align every probe inside each product without a reported probe site; returns the
        best new site of at least warning level per probe oligo and product."""
        by_id = {s.id: s for s in sites}
        known = _Known(sites)
        added: list[SiteResult] = []
        for a in amplicons:
            if a.classification == "likely_detected" or a.probe_site is not None:
                continue
            product = self._product(a)
            if product is None:
                continue
            anchor = by_id[a.left_site]
            note = f"found by re-aligning the probe inside product {a.id}; not reported by BLAST"
            for label in self._labels("probe"):
                s = self._best(
                    label, product, a.start, ("+", "-"), anchor, "probe", note,
                    accept=lambda s: s.level != "minor",
                )  # fmt: skip
                if s is None or known.overlaps(s):
                    continue
                s.id = f"S{next(self.ids)}"
                known.add(s)
                added.append(s)
        self.state.summary.probe_sites_added = len(added)
        return added
