"""From a run's results to the report's figures (report review 2026-11-20): the inputs of
:mod:`.charts`, built here so the chart functions take plain numbers and can be tested alone."""

from __future__ import annotations

from typing import Any

from markupsafe import Markup

from ..config import Config
from ..inclusivity.models import FragmentYear, fragment_window, status_last_year, status_years
from ..results import RunResult
from . import charts
from .grouping import amplicon_order


def _markup(svg: str) -> Markup | None:
    return Markup(svg) if svg else None  # noqa: S704 - SVG from numbers, names escaped


def _counts(y: Any) -> charts.Counts:
    return charts.Counts(
        detectable=y.detectable, at_risk=y.at_risk, likely_failure=y.likely_failure,
        deleted=getattr(y, "possible_deletion", 0), undetermined=y.undetermined,
    )  # fmt: skip


def tm_strip(result: RunResult, cfg: Config) -> Markup | None:
    """Tm per oligo against the primer bands (P1, oligo design row)."""
    status = {c.id: c.status.value for c in result.oligo_qc.checks}
    rows = [
        charts.TmRow(
            name=o.name or o.role,
            tm_min=o.tm_c_min,
            tm_max=o.tm_c_max,
            status=status.get(f"{o.name or o.role}.tm", "PASS"),
            primer=o.role != "probe",
        )  # fmt: skip
        for o in amplicon_order(result.oligo_qc.oligos)
    ]
    t = cfg.thresholds.primer.tm_c
    return _markup(
        charts.tm_strip(
            rows, tuple(t.pass_range), tuple(t.fail_range), cfg.reaction.annealing_temp_C
        )
    )


def window(result: RunResult, cfg: Config) -> Any:
    """The pooled status window of the whole fragment (None without one)."""
    inc = result.inclusivity
    if inc is None or not inc.exhaustive:
        return None
    return fragment_window(
        status_years(inc), cfg.inclusivity.verdict_window_years, status_last_year(inc)
    )


def window_meter(result: RunResult, cfg: Config) -> Markup | None:
    """The status window against the limits (P1, target detection row)."""
    w = window(result, cfg)
    if w is None:
        return None
    return _markup(
        charts.window_meter(
            _counts(w), cfg.inclusivity.warn_below_percent, cfg.inclusivity.fail_below_percent
        )
    )


def coverage_steps(result: RunResult, cfg: Config) -> Markup | None:
    """Listed, assessed, region found, judged in the status window (P1, coverage row)."""
    vs = result.variant_summary
    c = vs.coverage if vs else None
    if c is None:
        return None
    steps = [("listed", c.listed_total), ("assessed", c.assessed_total),
             ("region found", c.found)]  # fmt: skip
    w = window(result, cfg)
    inc = result.inclusivity
    axis = "collected" if inc is not None and inc.status_axis == "collection" else "released"
    span = (f"{axis} {w.first}–{w.last}", w.n) if w is not None else None
    return _markup(charts.coverage_steps(steps, span))


def year_bars(result: RunResult, cfg: Config) -> Markup | None:
    """Outcome per year on the status axis, the window bracketed (P2)."""
    inc = result.inclusivity
    w = window(result, cfg)
    if inc is None or w is None:
        return None
    few_below = cfg.inclusivity.min_genomes_per_year
    rows = [
        charts.YearRow(
            label=str(y.year),
            counts=_counts(y),
            in_window=w.first <= y.year <= w.last,
            few=_counts(y).judged < few_below,
        )  # fmt: skip
        for y in status_years(inc)
    ]
    axis = "collection" if inc.status_axis == "collection" else "release"
    if axis == "collection" and inc.collection is not None:  # dates that place no genome
        extras = [
            charts.YearRow(label=name, counts=_counts(extra))  # not a year: not drawn pale
            for extra, name in ((inc.collection.undated, "no usable date"),
                                (inc.collection.earlier, f"before {inc.collection.first_year}"))
            if isinstance(extra, FragmentYear) and (extra.with_region or extra.possible_deletion)
        ]  # fmt: skip
        rows = [*extras, *rows]  # first, as in Part B (user, 2026-11-26)
    return _markup(charts.year_bars(rows, title=f"Outcome per {axis} year"))


PANEL_W = 600  # two fit side by side on screen (user, 2026-11-26); stacked in print


def year_panels(result: RunResult, cfg: Config) -> dict[str, Any] | None:
    """Part B's two year figures, full width one under the other (third report review,
    2026-11-25; user, 2026-11-26: side by side they were too small): by release year and by
    collection year, the status axis bracketed; in the collection figure the records collected
    before the window and those without a usable date come first, as bars of their own (not
    years, so not drawn pale). The numbers: workbook, sheet "Inclusivity"."""
    inc = result.inclusivity
    w = window(result, cfg)
    if inc is None or w is None or not inc.fragment_years:
        return None
    few_below = cfg.inclusivity.min_genomes_per_year
    by_collection = inc.status_axis == "collection"

    def rows(years: list[FragmentYear], status: bool) -> list[charts.YearRow]:
        return [
            charts.YearRow(label=str(y.year), counts=_counts(y),
                           in_window=status and w.first <= y.year <= w.last,
                           few=_counts(y).judged < few_below)
            for y in years
        ]  # fmt: skip

    release = charts.year_bars(rows(inc.fragment_years, not by_collection), width=PANEL_W,
                               title="By release year")  # fmt: skip
    collection = ""
    ca = inc.collection
    if ca is not None:
        # chronological (user, 2026-11-26): no date first, then before the window, then the years
        extra = [
            charts.YearRow(label=name, counts=_counts(y))
            for y, name in ((ca.not_read, "date not read"), (ca.undated, "no usable date"),
                            (ca.earlier, f"before {ca.first_year}"))
            if y.with_region or y.possible_deletion
        ]  # fmt: skip
        collection = charts.year_bars([*extra, *rows(ca.years, by_collection)], width=PANEL_W,
                                      title="By collection year")  # fmt: skip
    return {
        "release": Markup(release),  # noqa: S704 - SVG from numbers, labels escaped
        "collection": Markup(collection) if collection else None,  # noqa: S704
        "status": "collection" if by_collection else "release",
        "window": w,
    }


def mismatch_columns(result: RunResult) -> list[tuple[str, str, str, int, dict[int, Any]]]:
    """Per oligo of the assay: ``(name, role, sequence, judged genomes, {base index: column})``,
    from the per-oligo variant rows (every judged genome's best copy). A mismatch counts at its
    oligo base with the class of the whole site; a base matching through a degenerate code is not
    a mismatch; a gap counts at the base it lies at (an inserted template base: the base before)."""
    vs = result.variant_summary
    if vs is None:
        return []
    by_name: dict[str, list[Any]] = {}
    roles: dict[str, str] = {}
    for o in vs.oligos:
        for row in o.rows:
            name = row.oligo_name or o.oligo
            by_name.setdefault(name, []).append(row)
            roles[name] = o.role
    out = []
    for oligo in result.assay.amplicon_list:
        rows = by_name.get(oligo.name)
        if not rows:
            continue
        columns: dict[int, charts.SiteColumn] = {}
        judged = 0
        for row in rows:
            judged += row.count
            pos = 0
            for q, s, m in zip(row.q_aln, row.s_aln, row.midline.ljust(len(row.q_aln)),
                               strict=False):  # fmt: skip
                if q == "-":
                    columns.setdefault(max(0, pos - 1), charts.SiteColumn()).gaps += row.count
                    continue
                if s == "-":
                    columns.setdefault(pos, charts.SiteColumn()).gaps += row.count
                elif m == " " and s != ".":
                    col = columns.setdefault(pos, charts.SiteColumn())
                    cls = row.grade or "indeterminate"
                    cls = "tolerated" if cls == "perfect" else cls
                    col.by_class[cls] = col.by_class.get(cls, 0) + row.count
                pos += 1
        out.append((oligo.name, roles[oligo.name], oligo.sequence, judged, columns))
    return out


def site_maps(result: RunResult) -> list[Markup]:
    """Per oligo, where the target genomes differ from it (P3)."""
    out = []
    for name, role, seq, judged, columns in mismatch_columns(result):
        svg = charts.site_map(name, seq, judged, columns, 0 if role == "probe" else 5)
        if svg:
            out.append(Markup(svg))  # noqa: S704 - SVG from numbers, names escaped
    return out


def mismatch_rows(result: RunResult) -> list[list[object]]:
    """The site maps' numbers for the workbook: one row per oligo base with a mismatch or gap."""
    rows: list[list[object]] = []
    for name, _role, seq, judged, columns in mismatch_columns(result):
        for i in sorted(columns):
            c = columns[i]
            rows.append([name, i + 1, -(len(seq) - i), seq[i], judged, c.total,
                         c.by_class.get("tolerated", 0), c.by_class.get("at_risk", 0),
                         c.by_class.get("likely_failure", 0), c.by_class.get("indeterminate", 0),
                         c.gaps])  # fmt: skip
    return rows


def closest_by_tier(sites: list[Any]) -> dict[str, Any]:
    """Per tier, the closest primer site that can prime (warning or critical level): fewest
    mismatches and gaps, then the longest clean 3' end, then the site id, so that Part A's glyph
    and the tier table always show the same site (user, 2026-11-25); worst-case partial sites,
    without a full alignment, left out."""
    best: dict[str, Any] = {}
    for s in sites:
        if s.role == "probe" or s.source == "blast_partial_worst_case" or not s.q_aln:
            continue
        if s.level not in ("warning", "critical"):  # a minor site cannot prime
            continue
        key = (s.n_mismatch + s.n_gap, -s.clean_3prime_nt, s.id)
        if s.tier not in best or key < (
            best[s.tier].n_mismatch + best[s.tier].n_gap, -best[s.tier].clean_3prime_nt,
            best[s.tier].id,
        ):  # fmt: skip
            best[s.tier] = s
    return best


def _zones(cfg: Config) -> charts.Zones:
    c, w = cfg.specificity.primer_site.critical, cfg.specificity.primer_site.warning
    return charts.Zones(crit_mm=c.max_mismatches, crit_gaps=c.max_gaps,
                        crit_clean=c.min_clean_3prime_nt, warn_mm=w.max_mismatches,
                        warn_gaps=w.max_gaps, warn_clean=w.min_clean_3prime_nt)  # fmt: skip


def _primer_length(result: RunResult) -> int:
    return max((len(o.sequence) for o in result.assay.oligo_list if o.role != "probe"),
               default=24)  # fmt: skip


def _point(s: Any, label: str) -> charts.MapPoint:
    return charts.MapPoint(
        label=label, tier=s.tier, mismatches=s.n_mismatch, clean3=s.clean_3prime_nt,
        gaps=s.n_gap, level=s.level,
        title=(f"{label}: closest primer site {s.query} on {s.accession}, {s.n_mismatch} "
               f"mismatch(es), {s.n_gap} gap(s), {s.clean_3prime_nt} clean 3′ nt, {s.level}"),
    )  # fmt: skip


MAP_POINTS = 40  # marks in the off-target site map; the rest in the workbook
_LEVEL_RANK = {"critical": 0, "warning": 1, "minor": 2}


def _site_rank(s: Any) -> tuple[Any, ...]:
    """An organism's closest site: the highest level first, then the fewest mismatches and gaps
    and the longest clean 3' end (user, 2026-11-26: by mismatches alone a minor site with no
    clean 3' end stood for an organism with 577 warning sites)."""
    return (_LEVEL_RANK.get(s.level, 3), s.n_mismatch + s.n_gap, -s.clean_3prime_nt, s.id)


def site_level_map(result: RunResult, cfg: Config) -> dict[str, Any] | None:
    """Each off-target organism's closest primer site against the site levels (third report
    review, 2026-11-25, M1): one mark per tier and species, every level included, the probe sites
    as a line of text (no 3' rule applies to them)."""
    from .grouping import species_of, tier_name

    spec = result.specificity
    if spec is None:
        return None
    species = species_of(result.taxonomy_breakdown)
    best: dict[tuple[str, str], Any] = {}
    probes: dict[tuple[str, str], Any] = {}
    for s in spec.sites:
        if s.source == "blast_partial_worst_case" or not s.q_aln:
            continue
        name = (species.get(s.taxid) if s.taxid else None) or s.organism or "unknown organism"
        into = probes if s.role == "probe" else best
        if s.role == "probe" and s.level == "minor":
            continue
        old = into.get((s.tier, name))
        if old is None or _site_rank(s) < _site_rank(old):
            into[(s.tier, name)] = s
    if not best and not probes:
        return None
    ranked = sorted(best.items(), key=lambda kv: (_site_rank(kv[1]), kv[0]))
    shown = ranked[:MAP_POINTS]
    points = [_point(s, name) for (_tier, name), s in shown]
    for n, pt in enumerate(points, 1):
        pt.number = n
    key = [
        {"n": n, "organism": name, "tier": s.tier, "query": s.query, "accession": s.accession,
         "mismatches": s.n_mismatch, "gaps": s.n_gap, "clean3": s.clean_3prime_nt,
         "level": s.level}
        for n, ((_tier, name), s) in enumerate(shown, 1)
    ]  # fmt: skip
    svg = charts.site_level_map(points, _zones(cfg), _primer_length(result)) if points else ""
    probe_line = "; ".join(
        f"{name} ({tier_name(s.tier)}): {s.query}, {s.n_mismatch} mm"
        + (f", {s.n_gap} gap(s)" if s.n_gap else "") + f", {s.level}"
        for (_tier, name), s in sorted(probes.items(), key=lambda kv: (kv[1].n_mismatch, kv[0]))
    )  # fmt: skip
    return {
        "svg": Markup(svg) if svg else None,  # noqa: S704 - SVG from numbers, names escaped
        "n": len(points), "more": len(ranked) - len(shown), "probes": probe_line, "key": key,
    }  # fmt: skip


def site_glyphs(result: RunResult, cfg: Config | None = None) -> dict[str, Markup]:
    """Per tier, the closest primer site as a dot on the site-level zones (third report review,
    2026-11-25, M1b: in the cell glyph a perfect match was the emptiest picture)."""
    from ..config import load_config

    spec = result.specificity
    if spec is None:
        return {}
    cfg = cfg or load_config()
    out = {}
    for tier, s in closest_by_tier(spec.sites).items():
        p = _point(s, s.organism or "unknown organism")
        p.title = (f"closest {s.role} site: {s.n_mismatch} mismatch(es), {s.n_gap} gap(s), "
                   f"{s.clean_3prime_nt} clean 3′ nt, {s.level}, "
                   f"{s.organism or 'unknown'}")  # fmt: skip
        svg = charts.site_dot(p, _zones(cfg), _primer_length(result))
        if svg:
            out[tier] = Markup(svg)  # noqa: S704 - SVG from numbers, label escaped
    return out


_STRUCT_GROUP = {"hairpin": "hairpin", "homodimer": "self-dimer", "heterodimer": "dimer",
                 "end_dimer": "3′ end"}  # fmt: skip


def structure_strip(result: RunResult, cfg: Config) -> Markup | None:
    """Every hairpin and dimer against the review and limit temperatures (third report review,
    2026-11-25, M5); the flagged ones keep their sequence drawing in the table below it."""
    qc = result.oligo_qc
    if not qc.structures:
        return None
    t = cfg.thresholds.structures
    fail = t.fail_tm_c if t.fail_tm_c is not None else cfg.reaction.annealing_temp_C
    rows = [
        charts.StructRow(group=_STRUCT_GROUP.get(s.kind, s.kind),
                         label=" / ".join(s.subjects) if s.kind != "end_dimer"
                         else " on ".join(s.subjects),
                         tm=s.tm_c, status=s.status.value, found=s.found)
        for s in sorted(qc.structures, key=lambda s: list(_STRUCT_GROUP).index(s.kind)
                        if s.kind in _STRUCT_GROUP else 9)
    ]  # fmt: skip
    return _markup(charts.structure_strip(rows, t.warn_tm_c, fail))


def coverage_accounting(result: RunResult) -> Markup | None:
    """Where every listed record went, and per oligo and for the whole fragment how many genomes
    have a detectable copy (third report review, 2026-11-25, M6). A genome can lack a detectable
    copy for more than one oligo, so the per-oligo shortfalls need not add up to the escapes."""
    vs = result.variant_summary
    c = vs.coverage if vs else None
    if c is None or not c.listed_total:
        return None
    what = "records" if c.source == "blast_partitioned" else "assemblies"
    seen = c.found + c.contig_break + c.masked + c.related_only + c.not_found
    other = max(0, c.assessed_total - seen)
    waiting = max(0, c.listed_total - c.assessed_total)
    listed = charts.AcctBar(
        f"{c.listed_total:,} {what} listed",
        [("#5B7C99", c.found, "region found"), ("url(#q-und)", c.contig_break, "cut by an end"),
         ("url(#q-und)", c.masked, "hidden by N"), ("#B7C4CF", c.related_only, "related only"),
         ("url(#q-del)", c.not_found, "not found"), ("url(#q-und)", other, "other"),
         ("#FFFFFF", waiting, "not assessed yet")],
        "; ".join(f"{n:,} {name}" for n, name in (
            (c.found, "region found"), (c.not_found, "not found"),
            (c.related_only, "related only"), (c.contig_break, "cut by an end"),
            (c.masked, "hidden by N"), (other, "other"), (waiting, "not assessed yet"),
        ) if n),
    )  # fmt: skip
    bars = [listed]
    cc = c.copies
    if cc is not None and cc.genomes:
        roles = [r for r in ("forward", "probe", "reverse")
                 if any(o.role == r for o in cc.oligos)]  # fmt: skip
        first = True
        for role in roles:
            none = cc.role_none.get(role, 0)
            und = cc.role_undetermined.get(role, 0)
            names = [o.name for o in cc.oligos if o.role == role]
            label = f"{role} {names[0]}" if len(names) == 1 and names[0] != role else role
            bars.append(charts.AcctBar(
                label, [("#2F6FA8", cc.genomes - none - und, "detectable copy"),
                        ("url(#q-und)", und, "undetermined"),
                        ("url(#q-risk)", none, "no detectable copy")],
                f"{cc.genomes - none - und:,} · {none:,} without" + (f" · {und:,} undetermined"
                                                                     if und else ""),
                gap_before=first,
            ))  # fmt: skip
            first = False
        und = cc.undetermined
        bars.append(charts.AcctBar(
            "whole fragment", [("#2F6FA8", cc.with_detectable_copy, "detectable copy"),
                               ("url(#q-und)", und, "undetermined"),
                               ("url(#q-risk)", cc.escapes, "escapes")],
            f"{cc.with_detectable_copy:,} · {cc.escapes:,} escapes"
            + (f" · {und:,} undetermined" if und else ""),
        ))  # fmt: skip
    return _markup(charts.accounting(bars))
