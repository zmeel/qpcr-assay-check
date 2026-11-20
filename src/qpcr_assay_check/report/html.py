"""Self-contained HTML report (Jinja2, inline SVG chart; no scripts, no external requests)."""

from __future__ import annotations

import re
from typing import Any

import yaml
from jinja2 import Environment, PackageLoader, select_autoescape
from markupsafe import Markup, escape

from ..config import Config
from ..oligo.grade import CAVEAT as GRADE_CAVEAT
from ..oligo.grade import site_string
from ..results import CheckResult, RunResult
from ..specificity.variants import group_off_target_sites
from ..variants.exhaustive import channel_verdict, channels_shown
from ..verdict import STATUS_LABEL
from . import charts as svg
from . import figures
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
from .summary import summary_rows

TOLERATED_VARIANTS_SHOWN = 5  # per oligo; the other tolerated variants: one row (all in workbook)
GROUP_ROWS_SHOWN = 15  # further rows per grouped table (rows that can fail: always shown)
CLOSEST_VARIANTS_SHOWN = 5  # closest off-target binding variants shown (all in the workbook)
ATTENTION_ON_PAGE_ONE = 3  # "Needs attention" rows on the sign-off pages (all in Part B)

_GROUPS = [
    ("forward", "Forward primer"),
    ("reverse", "Reverse primer"),
    ("probe", "Probe"),
    ("pair", "Primer pair"),
    ("amplicon", "Amplicon"),
]


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
    The oligo itself is shown once, in the table header.

    A base that matches only through a degenerate code - the oligo's own (Y against C or T) or an
    ambiguity code in the genome - is written out in grey instead of a dot: it is a match, but it
    is not the same base, and two site variants that differ only there would otherwise be drawn
    identically (user, 2026-10-07)."""
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
        elif qc != sc:
            ch, klass = sc, "amb"  # a match through a degenerate code: shown, not a dot
        else:
            ch, klass = ".", ""
        classes = " ".join(c for c in (klass, "tail" if is_tail else "") if c)
        ch = str(escape(ch))
        out.append(f'<span class="{classes}">{ch}</span>' if classes else ch)
    if suffix:  # e.g. "(1)": which oligo of the role, as numbered in the column header
        out.append(f' <span class="meta">{escape(suffix)}</span>')
    return Markup(f'<pre class="aln compact">{"".join(out)}</pre>')  # noqa: S704 - escaped


def merge_binding_variants(groups: list[Any]) -> list[Any]:
    """Closest off-target variants of one oligo that bind the same way - the same mismatches
    (position and template base), gaps, unaligned bases and level - are one row: the degenerate
    variants of an oligo, or an unread N, differ only at bases that match (report review
    2026-11-20: 9 of 10 HSV-1 rows were the same HSV-2 primer site). The first, closest, is
    shown; ``merged`` counts the others. Sites are not summed: one site is reported once per
    variant that reaches it."""
    out: list[Any] = []
    index: dict[tuple, int] = {}
    for g in groups:
        pattern = tuple(
            (i, s) for i, (s, m) in enumerate(zip(g.s_aln, g.midline.ljust(len(g.s_aln)),
                                                   strict=False)) if m == " "
        )  # fmt: skip
        key = (re.sub(r"_v\d+$", "", g.query), g.level, g.n_gap, g.n_unaligned,
               g.clean_3prime_nt, pattern)  # fmt: skip
        if key in index:
            first = out[index[key]]
            first.merged += 1
            first.max_sites = max(first.max_sites, g.n_sites)
            continue
        index[key] = len(out)
        out.append(_Merged(g))
    return out


class _Merged:
    """A closest-site row and how many binding-identical variants it stands for."""

    def __init__(self, g: Any) -> None:
        self.g, self.merged, self.max_sites = g, 0, g.n_sites

    def __getattr__(self, name: str) -> Any:
        return getattr(self.g, name)


def floor_matrix(spec: Any) -> list[dict[str, Any]]:
    """The score floors as one row per tier and oligo (degenerate variants as a min-max range):
    the long per-tier sentence of every variant, in a table (report review 2026-11-20, P5)."""
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for e in spec.score_floors:
        name = re.sub(r"_v\d+$", "", e.query)
        r = rows.setdefault((e.tier, name), {"tier": e.tier, "oligo": name, "length": e.length,
                                             "scores": [], "mm": [], "list_full": False,
                                             "unknown": 0, "sources": set()})  # fmt: skip
        if e.min_score is not None:
            r["scores"].append(e.min_score)
        if e.max_mismatches_reported is not None:
            r["mm"].append(e.max_mismatches_reported)
        r["list_full"] = r["list_full"] or e.list_full
        r["unknown"] += e.searches_without_statistics
        r["sources"].add(e.space_source)

    def span(v: list[int]) -> str:
        return "–" if not v else str(v[0]) if min(v) == max(v) else f"{min(v)}–{max(v)}"

    out = []
    for r in rows.values():
        r["score"] = span(sorted(r["scores"]))
        r["mismatches"] = span(sorted(r["mm"]))
        r["source"] = ("upper bound" if "upper_bound" in r["sources"]
                       else "from hits" if "from_hits" in r["sources"] else "reported")  # fmt: skip
        out.append(r)
    return out


def floor_per_search(spec: Any) -> dict[str, str]:
    """Per tier of several searches: each search's taxa and floors (F6), as one sentence."""
    from ..specificity.reach import _per_search

    by: dict[str, list[Any]] = {}
    for e in spec.score_floors:
        by.setdefault(e.tier, []).append(e)
    return {t: _per_search(m).strip() for t, m in by.items() if _per_search(m)}


def qc_matrix(result: RunResult) -> dict[str, Any]:
    """The oligo checks as a matrix: one row per check, one column per oligo, the limit once
    (report review 2026-11-20, second round: one row per check and oligo repeated the oligo's
    name under its own heading and squeezed the check column to a word per line). Checks of the
    mix, the pair and the amplicon stay a short list."""
    oligos = result.oligo_qc.oligos
    names = [o.name or o.role for o in oligos]
    roles = {o.name or o.role: o.role for o in oligos}
    order: list[str] = []
    cells: dict[str, dict[str, CheckResult]] = {}
    labels: dict[str, str] = {}
    for c in result.oligo_qc.checks:
        if c.subject not in roles:
            continue
        key = c.id.split(".", 1)[1] if "." in c.id else c.id
        if key not in cells:
            order.append(key)
            label = c.name.replace(c.subject, "").strip()
            for word in ("Forward primer", "Reverse primer", "Forward", "Reverse", "Probe"):
                if label.startswith(word):
                    label = label[len(word) :].strip()
                    break
            label = label.lstrip("/ ").strip()
            labels[key] = label[:1].upper() + label[1:]
        cells.setdefault(key, {})[c.subject] = c
    rows = []
    for key in order:
        by = cells[key]
        rules: dict[str, list[str]] = {}
        for name, c in by.items():
            if c.rule:
                rules.setdefault(c.rule, []).append(roles[name])
        if len(rules) <= 1:
            limit = next(iter(rules), "")
        else:
            kinds = {"forward": "primers", "reverse": "primers", "probe": "probe"}
            limit = "; ".join(
                f"{'/'.join(sorted({kinds[r] for r in rs}))}: {rule}" for rule, rs in rules.items()
            )
        rows.append({
            "label": labels[key], "cells": [by.get(n) for n in names], "limit": limit,
            "flagged": [(n, c) for n, c in by.items()
                        if c.status.value in ("WARN", "FAIL") and c.message],
        })  # fmt: skip
    kinds = {"forward": "Forward", "reverse": "Reverse", "probe": "Probe"}
    others = []
    for key, title in [("mix", "Reaction mix"), *_GROUPS[3:]]:
        items = [c for c in result.oligo_qc.checks if c.subject == key]
        if items:
            others.append((title, items))
    return {
        "columns": [(n, kinds[roles[n]]) for n in names],
        "rows": rows,
        "others": others,
    }


def hits_per_query(spec: Any) -> list[dict[str, Any]]:
    """Per tier and query: BLAST hits, whether the list reached its size limit, whether
    relevant hits may have been cut (the list full and its weakest hit still relevant), the
    relevant alignments, how many were assessed, whether the site cap cut them, and what the
    search could report (report review 2026-11-20, second round: two tables called different
    things "Hit list full")."""
    reached: dict[tuple[str, str], bool] = {}
    cut: dict[tuple[str, str], bool] = {}
    hits: dict[tuple[str, str], int] = {}
    for r in spec.searches:
        for label, n in r["n_hits"].items():
            key = (r["tier"], label)
            hits[key] = hits.get(key, 0) + n
        for s in r["saturation"]:
            key = (r["tier"], s["label"])
            reached[key] = reached.get(key, False) or s["list_full"]
            cut[key] = cut.get(key, False) or s["saturated"]
    counts = {(c.tier, c.query): c for c in spec.counts}
    floors = {(f.tier, f.query): f for f in spec.score_floors}
    out = []
    for key, n in hits.items():
        c, f = counts.get(key), floors.get(key)
        out.append({
            "tier": key[0], "query": key[1], "hits": n,
            "list_reached": reached.get(key, False), "possibly_cut": cut.get(key, False),
            "relevant": c.hsps_relevant if c else None, "assessed": c.sites_assessed if c else None,
            "cut_by_cap": bool(c and c.truncated),
            "score": f.min_score if f else None,
            "mismatches": f.max_mismatches_reported if f else None,
            "space": f.space_source if f else "",
        })  # fmt: skip
    return out


def _flat(d: Any, prefix: str = "") -> dict[str, Any]:
    """A nested mapping as ``{"a.b.c": value}`` (lists kept as values)."""
    if not isinstance(d, dict):
        return {prefix: d}
    out: dict[str, Any] = {}
    for k, v in d.items():
        out.update(_flat(v, f"{prefix}.{k}" if prefix else str(k)))
    return out


#: (group, configuration path) of the limits a reviewer needs to read the record; the oligo
#: limits stand in the oligo QC table (report review 2026-11-20, second round)
LIMITS_SHOWN = [
    ("Reaction", "reaction.annealing_temp_C"), ("Reaction", "reaction.na_mM"),
    ("Reaction", "reaction.mg_mM"), ("Reaction", "reaction.dntp_mM"),
    ("Reaction", "reaction.primer_nM"), ("Reaction", "reaction.probe_nM"),
    ("Inclusivity", "inclusivity.status_axis"), ("Inclusivity", "inclusivity.warn_below_percent"),
    ("Inclusivity", "inclusivity.fail_below_percent"),
    ("Inclusivity", "inclusivity.verdict_window_years"),
    ("Inclusivity", "inclusivity.min_genomes_for_verdict"),
    ("Inclusivity", "inclusivity.min_genomes_per_year"),
    ("Inclusivity", "inclusivity.max_undetermined_percent"),
    ("Variants", "variants.homopolymer_bulges_detectable"), ("Variants", "variants.probe_channels"),
    ("Variants", "variants.judge_from_parts"),
    ("Off-target sites", "specificity.primer_site"), ("Off-target sites", "specificity.probe_site"),
    ("Off-target sites", "specificity.graded_off_target"),
    ("Off-target sites", "specificity.probe_binds_if"),
    ("Off-target sites", "specificity.cautious_tiers"),
    ("Off-target status", "specificity.severity"),
    ("Off-target status", "specificity.off_target_tiers"),
    ("Off-target status", "specificity.tier_waivers"),
    ("Search", "search.database"), ("Search", "search.expect"), ("Search", "search.word_size"),
    ("Search", "search.hitlist_size"), ("Search", "search.background_taxids"),
    ("Search caps", "specificity.max_sites_per_query"),
    ("Search caps", "specificity.max_amplicon_size"), ("Search caps", "specificity.max_amplicons"),
    ("Search caps", "specificity.partner_scan_max_windows"),
    ("Search caps", "specificity.probe_scan_max_products"),
]  # fmt: skip


def limits_applied(config: dict[str, Any]) -> list[tuple[str, str, str]]:
    """``(group, setting, value)`` for the limits of :data:`LIMITS_SHOWN` present in the
    record's configuration."""
    out = []
    for group, path in LIMITS_SHOWN:
        node: Any = config
        for part in path.split("."):
            node = node.get(part) if isinstance(node, dict) else None
        if node is not None:
            out.append((group, path.split(".", 1)[1], _plain(node)))
    return out


def differing_settings(result: RunResult) -> list[tuple[str, str, str, str]]:
    """``(setting, value, default, source)`` for every setting of the record that differs from
    the packaged defaults of this version, the operational ones (ncbi, report) left out as the
    inputs hash leaves them out; source: the assay file or a configuration file."""
    from ..config import load_config

    defaults = _flat(load_config().model_dump(mode="json"))
    used = _flat(result.config)
    from_assay = set(_flat(result.assay.settings or {}))
    out = []
    for key, value in used.items():
        if key.split(".", 1)[0] in ("ncbi", "report") or defaults.get(key) == value:
            continue
        source = (
            "assay file"
            if any(key == k or key.startswith(k + ".") for k in from_assay)
            else ("configuration file")
        )
        out.append((key, _plain(value), _plain(defaults.get(key, "–")), source))
    return out


def decision_lines(result: RunResult, summary: list[Any]) -> list[tuple[str, str]]:
    """``(status, text)`` for the sign-off: every finding that exceeds a limit or leaves
    evidence missing in full, then one line per check that needs review (report review
    2026-11-20, second round: 21 lines, 11 of them repeating Part B, pushed the decision box to a
    third page). The full list opens Part B."""
    out: list[tuple[str, str]] = []
    qc = result.oligo_qc
    for c in qc.checks:
        if c.status.value == "FAIL":
            out.append(("FAIL", c.message or f"{c.name}: {c.display} {c.unit}".strip()))
    for s in qc.structures:
        if s.status.value == "FAIL":
            out.append(("FAIL", f"{s.label}: structure Tm {s.tm_c} °C"))
    spec = result.specificity
    if spec is not None:
        for f in spec.findings:
            if f.severity in ("FAIL", "INCOMPLETE"):
                out.append((f.severity, f"Specificity: {f.message}"))
    for row in summary:
        if row.anchor == "specificity" or row.anchor == "oligo-qc":
            continue  # their findings are listed above
        if row.css in ("FAIL", "INCOMPLETE"):
            out.append((row.css, f"{row.check}: {row.reason or row.result}"))
    for row in summary:
        if row.css == "WARN":
            out.append(("WARN", f"{row.check}: {row.reason or row.result} (details in Part B)"))
    return out


def _plain(value: Any) -> str:
    """A value as plain text: "key value; key value", lists comma-separated (not Python
    notation: the record is read by people, report review 2026-11-20, second round)."""
    if isinstance(value, dict):
        return "; ".join(f"{k} {_plain(v)}" for k, v in value.items())
    if isinstance(value, list | tuple):
        return ", ".join(_plain(v) for v in value) or "none"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


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
    env.filters["plain"] = _plain
    env.tests["search"] = lambda value, text: text in str(value)
    return env


def _channel_table(result: RunResult, cfg: Config) -> list[tuple[Any, Any, str]]:
    """``(channel result, status, reason)`` rows when the channels differ in anything."""
    c = result.variant_summary.coverage if result.variant_summary else None
    if not channels_shown(c):
        return []
    return [(r, *channel_verdict(r, cfg.inclusivity, c.complete))  # type: ignore[union-attr]
            for r in c.channel_results]  # type: ignore[union-attr]  # fmt: skip


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
        strip = figures.tm_strip(result, cfg)
        if strip:
            charts.append(
                {
                    "title": "Melting temperatures",
                    "html": strip,
                    "caption": (
                        "Nearest-neighbour Tm per oligo: a dot, or a line over the range of a "
                        "degenerate oligo's variants (a triangle when its Tm check is outside the "
                        "limit; probes hollow, as the primer bands do not apply to them). Shaded: "
                        "the preferred primer range; solid lines: the primer limits; dashed: the "
                        "annealing temperature. The values are in the checks below."
                    ),
                }
            )

    spec = result.specificity
    shown: list[Any] = []
    hidden = hidden_sites = 0
    if spec is not None:
        grouped = merge_binding_variants(group_off_target_sites(spec.sites))
        limit = CLOSEST_VARIANTS_SHOWN
        shown, hidden = grouped[:limit], max(0, len(grouped) - limit)
        hidden_sites = sum(g.max_sites for g in grouped[limit:])
    species = species_of(result.taxonomy_breakdown)
    product_groups = (
        group_products(spec.amplicons, {s.id: s for s in spec.sites}, species) if spec else []
    )
    site_groups = group_sites(spec.sites, species) if spec else []
    vs = result.variant_summary
    fragments = (
        fragment_view(
            vs.fragments,
            vs.fragment_total,
            cfg.variants.homopolymer_bulges_detectable,
            oligos=vs.oligos,
        )  # fmt: skip
        if vs and vs.fragments
        else None
    )
    rows_of_searches = _search_rows(spec) if spec is not None else []
    evidence_rows = [
        (e, sum(r.count for o in (vs.oligos if vs else []) for r in o.rows
                if r.oligo_name == e.oligo and site_string(r.q_aln, r.s_aln) == e.variant))
        for e in result.assay.evidence
    ]  # fmt: skip
    grade_counts: dict[str, dict[str, int]] = {}
    for i, o in enumerate(vs.oligos if vs else []):
        counts: dict[str, int] = {}
        for row in o.rows:
            if row.grade and row.grade != "perfect":
                counts[row.grade] = counts.get(row.grade, 0) + row.count
        grade_counts[f"{o.role}|{i}"] = counts
    figs: dict[str, Any] = {}
    if cfg.report.include_charts:
        figs = {
            "tm": figures.tm_strip(result, cfg),
            "window": figures.window_meter(result, cfg),
            "coverage": figures.coverage_steps(result, cfg),
            "years": figures.year_bars(result, cfg),
            **{f"tier:{t}": g for t, g in figures.site_glyphs(result).items()},
        }
    template = _environment().get_template("report.html.j2")
    return template.render(
        figures=figs,
        chart_defs=Markup(svg.defs()) if figs else "",  # noqa: S704 - constant SVG
        site_maps=figures.site_maps(result) if cfg.report.include_charts else [],
        attention_shown=ATTENTION_ON_PAGE_ONE,
        grade_counts=grade_counts,
        qc_rows=qc_matrix(result),
        decisions=decision_lines(
            result,
            summary_rows(
                result, cfg, spec_overview(spec, result.assay, rows_of_searches) if spec else []
            ),
        ),
        limits=limits_applied(result.config),
        differing=differing_settings(result),
        incomplete_queries=[
            q
            for q in (hits_per_query(spec) if spec else [])
            if q["possibly_cut"] or q["cut_by_cap"]
        ],
        site_by_id={s.id: s for s in spec.sites} if spec else {},
        floors=floor_matrix(spec) if spec else [],
        floor_searches=floor_per_search(spec) if spec else {},
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
        evidence_rows=evidence_rows,
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
        assay_settings_yaml=(
            yaml.safe_dump(result.assay.settings, sort_keys=False, allow_unicode=True)
            if result.assay.settings
            else ""
        ),
        status_label=STATUS_LABEL[result.overall.verdict],
        channel_table=_channel_table(result, cfg),
        summary=summary_rows(
            result, cfg, spec_overview(spec, result.assay, rows_of_searches) if spec else []
        ),
    )
