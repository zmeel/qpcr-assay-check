"""Turn assessed sites and predicted products into findings and a transparent verdict.

Severities come from ``specificity.severity`` in the configuration. Evidence that is missing (a
saturated hit list, a truncated assessment, a window that could not be fetched) is reported as
INCOMPLETE and never as a pass. Precedence: FAIL > INCOMPLETE > WARN > PASS.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable

from ..config import SpecificitySettings
from ..verdict import Verdict
from .models import AmpliconResult, Finding, SiteResult, TierCount


def verdict_of(findings: Iterable[Finding], topics: set[str] | None = None) -> Verdict:
    """Combine findings (optionally only some topics) into a verdict."""
    chosen = [f for f in findings if topics is None or f.topic in topics]
    severities = {f.severity for f in chosen}
    if "FAIL" in severities:
        return Verdict.FAIL
    if "INCOMPLETE" in severities:
        return Verdict.INCOMPLETE
    if "WARN" in severities:
        return Verdict.WARN
    return Verdict.PASS


def describe_site(s: SiteResult) -> str:
    """One-line description of a site for messages."""
    tm = ""
    if s.tm_c is not None:
        delta = f", {s.delta_tm_c:+.1f} °C vs perfect" if s.delta_tm_c is not None else ""
        tm = f", duplex Tm {s.tm_c:.1f} °C{delta}"
    partial = f", {s.n_unaligned} nt unaligned (worst case)" if s.n_unaligned else ""
    return (
        f"{s.role} on {s.accession} ({s.organism or 'unknown organism'}): "
        f"{s.n_mismatch} mismatch(es), {s.n_gap} gap(s), {s.clean_3prime_nt} clean 3' nt"
        f"{tm}{partial}"
    )


def _closest(sites: list[SiteResult]) -> SiteResult:
    return min(sites, key=lambda s: (s.n_mismatch + s.n_gap, -s.clean_3prime_nt, s.id))


def build_findings(
    *,
    sites: list[SiteResult],
    amplicons: list[AmpliconResult],
    site_by_id: dict[str, SiteResult],
    counts: list[TierCount],
    saturated: list[tuple[str, str, str]],
    off_tiers_seen: list[str],
    intended_target: dict[str, int],
    target_searched: bool,
    oligo_roles: dict[str, str] | None = None,
    n_primer_only: int,
    n_fetch_failed: int,
    amplicons_truncated: bool,
    rules: SpecificitySettings,
) -> list[Finding]:
    """All findings, most severe first within each topic."""
    sev = rules.severity
    out: list[Finding] = []

    scope = f"Off-target tiers assessed: {', '.join(off_tiers_seen) or 'none'}."
    not_searched = [t for t in rules.off_target_tiers if t not in off_tiers_seen]
    if not_searched:
        scope += (
            f" Configured off-target tiers not searched in this run: {', '.join(not_searched)}."
        )
    out.append(Finding(severity="INFO", message=scope, topic="search"))
    if not off_tiers_seen:
        out.append(
            Finding(
                severity="INCOMPLETE",
                message="No off-target tier was searched, so specificity cannot be assessed.",
                topic="search",
            )
        )

    by_tier: dict[str, list[str]] = defaultdict(list)
    for tier, label, _note in saturated:
        by_tier[tier].append(label)
    for tier, labels in by_tier.items():
        out.append(
            Finding(
                severity="INCOMPLETE",
                message=(
                    f"Tier '{tier}': the BLAST hit list is saturated for "
                    f"{', '.join(sorted(labels))}; relevant hits may be missing. Reduce the "
                    "taxa per search or raise the hit-list size."
                ),
                topic="search",
            )
        )
    for c in counts:
        if c.truncated:
            out.append(
                Finding(
                    severity="INCOMPLETE",
                    message=(
                        f"Tier '{c.tier}', {c.query}: {c.hsps_relevant} relevant alignments, "
                        f"only the {c.sites_assessed} strongest were assessed "
                        "(max_sites_per_query)."
                    ),
                    topic="search",
                )
            )
    if n_fetch_failed:
        out.append(
            Finding(
                severity="INCOMPLETE",
                message=(
                    f"{n_fetch_failed} sequence window(s) could not be fetched; those hits were "
                    "assessed with worst-case assumptions and should be re-checked."
                ),
                topic="search",
            )
        )

    # ---- site findings
    groups: dict[tuple[str, str, str], list[SiteResult]] = defaultdict(list)
    for s in sites:
        if s.level == "minor":
            continue
        kind = "probe" if s.role == "probe" else "primer"
        groups[(s.tier, kind, s.level)].append(s)
    for (tier, kind, level), members in sorted(groups.items()):
        if kind == "primer":
            severity = sev.primer_site_critical if level == "critical" else sev.primer_site_warning
        else:
            severity = sev.probe_site_critical if level == "critical" else "INFO"
        out.append(
            Finding(
                severity=severity,
                message=(
                    f"Tier '{tier}': {len(members)} {level} {kind} site(s); closest: "
                    f"{describe_site(_closest(members))}."
                ),
                topic="sites",
            )
        )

    # ---- amplicon findings
    by_class: dict[tuple[str, str], list[AmpliconResult]] = defaultdict(list)
    for a in amplicons:
        by_class[(a.tier, a.classification)].append(a)
    for (tier, cls), members in sorted(by_class.items()):
        first = members[0]
        left, right = site_by_id.get(first.left_site), site_by_id.get(first.right_site)
        detail = ""
        if left and right:
            detail = (
                f" (e.g. {first.length} bp on {first.accession}, {first.organism or 'unknown'}; "
                f"{first.roles} with {left.n_mismatch}+{right.n_mismatch} mismatches)"
            )
        if cls == "likely_detected":
            out.append(
                Finding(
                    severity=sev.amplicon_likely_detected,
                    message=(
                        f"Tier '{tier}': {len(members)} predicted off-target product(s) that both "
                        f"primers and the probe should give signal for{detail}."
                    ),
                    topic="amplicons",
                )
            )
        else:
            out.append(
                Finding(
                    severity=sev.amplicon_not_detected,
                    message=(
                        f"Tier '{tier}': {len(members)} predicted off-target product(s) "
                        "amplified by both primers but unlikely to be detected by the probe"
                        f"{detail}."
                    ),
                    topic="amplicons",
                )
            )
    if amplicons_truncated:
        out.append(
            Finding(
                severity="INCOMPLETE",
                message="The list of predicted products was cut at max_amplicons.",
                topic="amplicons",
            )
        )
    if n_primer_only:
        out.append(
            Finding(
                severity="INFO",
                message=(
                    f"{n_primer_only} primer site(s) at warning or critical level formed no "
                    "product (no facing partner within the maximum amplicon size)."
                ),
                topic="amplicons",
            )
        )
    if target_searched:
        # hits per oligo name (degenerate variants summed); a role is missing only when none of
        # its oligos (alternatives in the mix) has a perfect hit
        roles = oligo_roles or {r: r for r in ("forward", "reverse", "probe")}
        per_oligo: dict[str, int] = dict.fromkeys(roles, 0)
        for label, n in intended_target.items():
            name = re.sub(r"_v\d+$", "", label)
            per_oligo[name] = per_oligo.get(name, 0) + n
        per_role: dict[str, int] = dict.fromkeys(("forward", "reverse", "probe"), 0)
        for name, n in per_oligo.items():
            role = roles.get(name, name)
            per_role[role] = per_role.get(role, 0) + n
        missing = sorted(r for r in ("forward", "reverse", "probe") if per_role.get(r, 0) == 0)
        shown = ", ".join(f"{k} {v}" for k, v in per_oligo.items())
        out.append(
            Finding(
                severity="INFO" if not missing else "WARN",
                message=(
                    f"Intended target: hits with a perfect full-length match per oligo: {shown}."
                    if not missing
                    else (
                        "Intended target: no perfect full-length hit for "
                        f"{', '.join(missing)} (hits per oligo: {shown}). The assay may not match "
                        "its intended target exactly, the target taxon may be wrong, or the hit "
                        "list was cut; check before relying on any other result."
                    )
                ),
                topic="search",
            )
        )
    return out
