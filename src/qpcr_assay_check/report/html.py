"""Self-contained HTML report (Jinja2, inline SVG chart; no scripts, no external requests)."""

from __future__ import annotations

from typing import Any

import yaml
from jinja2 import Environment, PackageLoader, select_autoescape
from markupsafe import Markup, escape

from ..config import Config
from ..oligo.grade import CAVEAT as GRADE_CAVEAT
from ..results import CheckResult, RunResult
from ..specificity.variants import LIST_FULL_NOTE, group_off_target_sites
from . import plots
from .grouping import (
    fragment_view,
    group_products,
    group_sites,
    oligo_view,
    shown_rows,
    site_changes,
    site_frequency,
    spec_overview,
    species_of,
)
from .ncbi_links import linkify, taxon_link

TOLERATED_VARIANTS_SHOWN = 5  # per oligo; the other tolerated variants: one row (all in workbook)
GROUP_ROWS_SHOWN = 15  # further rows per grouped table (rows that can fail: always shown)
CLOSEST_VARIANTS_SHOWN = 10  # closest off-target binding variants shown (all in the workbook)

_GROUPS = [
    ("forward", "Forward primer"),
    ("reverse", "Reverse primer"),
    ("probe", "Probe"),
    ("pair", "Primer pair"),
    ("amplicon", "Amplicon"),
]

VERDICT_MEANING = {
    "PASS": "Every evaluated check passed and every required analysis was run.",
    "WARN": "No check failed, but at least one raised a warning. Review the findings.",
    "FAIL": "At least one check failed. See the findings below.",
    "INCOMPLETE": (
        "Required analyses were not evaluated, so this result is not a pass. "
        "Evidence that is missing never counts as a PASS."
    ),
}


def _seq_html(seq: str, tail: int = 5) -> Markup:
    """5'-…-3' with the last ``tail`` nt (the 3' end) emphasised."""
    s = str(escape(seq))
    if 0 < tail < len(s):
        s = f'{s[:-tail]}<b class="tail">{s[-tail:]}</b>'
    return Markup(f'<span class="seq">5′-{s}-3′</span>')  # noqa: S704 - content escaped above


def _alignment_html(site: Any, tail: int = 5) -> Markup:
    """Three-line alignment: oligo, match line, subject; mismatches marked, 3' end emphasised.

    Columns belonging to the last ``tail`` oligo bases are underlined; mismatched subject bases
    are highlighted, gaps shaded, and unaligned (not re-aligned) positions shown as dots.
    """
    if getattr(site, "role", None) == "probe":
        tail = 0  # a hydrolysis probe is not extended: no 3' end to emphasise
    q, s, mid = site.q_aln, site.s_aln, site.midline
    n_oligo = sum(c != "-" for c in q)
    seen = 0
    lines: list[list[str]] = [[], [], []]
    for qc, sc, mc in zip(q, s, mid.ljust(len(q)), strict=True):
        is_tail = tail > 0 and qc != "-" and seen >= n_oligo - tail
        if qc != "-":
            seen += 1
        elif tail > 0 and seen >= n_oligo - tail:
            is_tail = True
        if sc == ".":
            klass = "un"
        elif qc == "-" or sc == "-":
            klass = "gp"
        elif mc == " ":
            klass = "mm"
        else:
            klass = ""
        for row, ch, k in ((0, qc, ""), (1, mc, ""), (2, sc, klass)):
            classes = " ".join(c for c in (k, "tail" if is_tail else "") if c)
            ch = str(escape(ch)) if ch != " " else "&nbsp;"
            lines[row].append(f'<span class="{classes}">{ch}</span>' if classes else ch)
    return Markup(  # noqa: S704 - every character was escaped above
        '<pre class="aln">'
        f"5′ {''.join(lines[0])} 3′\n   {''.join(lines[1])}\n   {''.join(lines[2])}"
        "</pre>"
    )


def _compact_html(site: Any, tail: int = 5, suffix: str = "") -> Markup:
    """One-line alignment for narrow tables: the subject in oligo orientation with matching
    bases as dots, mismatches as highlighted letters and gaps as '-'; the 3' end underlined.
    The oligo itself is shown once, in the table header."""
    if getattr(site, "role", None) == "probe":
        tail = 0
    q, s, mid = site.q_aln, site.s_aln, site.midline
    n_oligo = sum(c != "-" for c in q)
    seen = 0
    out: list[str] = []
    for qc, sc, mc in zip(q, s, mid.ljust(len(q)), strict=True):
        is_tail = tail > 0 and (seen >= n_oligo - tail)
        if qc != "-":
            seen += 1
        if sc == ".":
            ch, klass = ".", "un"
        elif qc == "-" or sc == "-":
            ch, klass = sc if sc != "-" else "-", "gp"
        elif mc == " ":
            ch, klass = sc, "mm"
        else:
            ch, klass = ".", ""
        classes = " ".join(c for c in (klass, "tail" if is_tail else "") if c)
        ch = str(escape(ch))
        out.append(f'<span class="{classes}">{ch}</span>' if classes else ch)
    if suffix:  # e.g. "(1)": which oligo of the role, as numbered in the column header
        out.append(f' <span class="meta">{escape(suffix)}</span>')
    return Markup(f'<pre class="aln compact">{"".join(out)}</pre>')  # noqa: S704 - escaped


def _search_rows(spec: Any) -> list[dict[str, Any]]:
    """Searches grouped by tier for the report table."""
    tiers: dict[str, dict[str, Any]] = {}
    for r in spec.searches:
        t = tiers.setdefault(
            r["tier"],
            {
                "tier": r["tier"], "taxids": [], "rids": [], "hits": {}, "saturated": [], "n": 0,
                "descriptions": 0, "in_requested": 0, "other": 0, "no_taxid": 0,
            },
        )  # fmt: skip
        res = r.get("restriction")
        if res:
            t["descriptions"] += res["n_descriptions"]
            t["in_requested"] += res["n_taxid_in_requested"]
            t["other"] += res["n_taxid_other"]
            t["no_taxid"] += res["n_without_taxid"]
        t["n"] += 1
        t["taxids"] += [x for x in r["taxids"] if x not in t["taxids"]]
        if r.get("rid"):
            t["rids"].append((r["rid"], (r.get("submitted_at") or "")[:10]))
        for label, n in r["n_hits"].items():
            t["hits"][label] = t["hits"].get(label, 0) + n
        t["saturated"] += [s["label"] for s in r["saturation"] if s["saturated"]]
    return list(tiers.values())


def _tm(value: float | None) -> str:
    if value is None:
        return "none"
    return "< 0" if value < 0 else f"{value:.1f}"


def _dg(value: float | None) -> str:
    return "" if value is None else f"{value:+.2f}"


def _environment() -> Environment:
    env = Environment(
        loader=PackageLoader("qpcr_assay_check.report", "templates"),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["seq_html"] = _seq_html
    env.filters["aln_html"] = _alignment_html
    env.filters["aln_compact"] = _compact_html
    env.filters["changes"] = site_changes
    env.filters["tm"] = _tm
    env.filters["dg"] = _dg
    env.filters["ncbi"] = linkify
    env.filters["taxon"] = taxon_link
    return env


def render_report(result: RunResult, cfg: Config) -> str:
    """Render the evaluation record as one self-contained HTML document."""
    groups: list[tuple[str, list[CheckResult]]] = []
    kinds = {"forward": "Forward primer", "reverse": "Reverse primer", "probe": "Probe"}
    oligo_groups = [
        (o.name or o.role, kinds[o.role] if not o.name or o.name == o.role
         else f"{kinds[o.role]} {o.name}")
        for o in result.oligo_qc.oligos
    ]  # fmt: skip
    for key, title in [*oligo_groups, ("mix", "Reaction mix"), *_GROUPS[3:]]:
        items = [c for c in result.oligo_qc.checks if c.subject == key]
        if items:
            groups.append((title, items))

    charts: list[dict[str, Any]] = []
    if cfg.report.include_charts:
        html = plots.tm_chart(result, cfg)
        if html:
            charts.append(
                {
                    "title": "Melting temperatures",
                    "html": Markup(html),  # noqa: S704 - SVG from numbers, names escaped
                    "caption": (
                        "Bars show nearest-neighbour Tm (range bars for degenerate oligos). "
                        "The shaded band is the primer PASS range; the dashed line is the "
                        "annealing temperature."
                    ),
                }
            )

    spec = result.specificity
    shown: list[Any] = []
    hidden = hidden_sites = 0
    if spec is not None:
        grouped = group_off_target_sites(spec.sites)
        limit = CLOSEST_VARIANTS_SHOWN
        shown, hidden = grouped[:limit], max(0, len(grouped) - limit)
        hidden_sites = sum(g.n_sites for g in grouped[limit:])
    species = species_of(result.taxonomy_breakdown)
    product_groups = (
        group_products(spec.amplicons, {s.id: s for s in spec.sites}, species) if spec else []
    )
    site_groups = group_sites(spec.sites, species) if spec else []
    vs = result.variant_summary
    fragments = (
        fragment_view(vs.fragments, vs.fragment_total, cfg.variants.homopolymer_bulges_detectable)
        if vs and vs.fragments
        else None
    )
    rows_of_searches = _search_rows(spec) if spec is not None else []
    template = _environment().get_template("report.html.j2")
    return template.render(
        r=result,
        product_groups=product_groups,
        fragments=fragments,
        site_groups=site_groups,
        rows_shown=GROUP_ROWS_SHOWN,
        products_shown=shown_rows(product_groups, "n_detected", GROUP_ROWS_SHOWN),
        sites_shown=shown_rows(site_groups, "n_critical", GROUP_ROWS_SHOWN),
        grade_caveat=GRADE_CAVEAT,
        oligo_views=[oligo_view(o, top_tolerated=TOLERATED_VARIANTS_SHOWN) for o in vs.oligos]
        if vs
        else [],
        site_pct=site_frequency(vs.oligos) if vs else {},
        tolerated_shown=TOLERATED_VARIANTS_SHOWN,
        list_full_note=LIST_FULL_NOTE,
        qc=result.oligo_qc,
        assay=result.assay,
        groups=groups,
        spec=spec,
        shown_variants=shown,
        hidden_variants=hidden,
        hidden_variant_sites=hidden_sites,
        search_rows=rows_of_searches,
        spec_overview=spec_overview(spec, result.assay, rows_of_searches) if spec else [],
        pending=[s for s in result.sections if s.state != "evaluated"],
        charts=charts,
        config_yaml=yaml.safe_dump(result.config, sort_keys=False, allow_unicode=True),
        assay_settings_yaml=(
            yaml.safe_dump(result.assay.settings, sort_keys=False, allow_unicode=True)
            if result.assay.settings
            else ""
        ),
        verdict_meaning=VERDICT_MEANING[result.overall.verdict.value],
    )
