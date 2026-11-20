"""From a run's results to the report's figures (report review 2026-11-20): the inputs of
:mod:`.charts`, built here so the chart functions take plain numbers and can be tested alone."""

from __future__ import annotations

from typing import Any

from markupsafe import Markup

from ..config import Config
from ..inclusivity.models import FragmentYear, fragment_window, status_last_year, status_years
from ..results import RunResult
from . import charts


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
        for o in result.oligo_qc.oligos
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
    if w is not None:
        steps.append(("judged, window", w.n))
    return _markup(charts.coverage_steps(steps))


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
        for extra, name in ((inc.collection.earlier, f"before {inc.collection.first_year}"),
                            (inc.collection.undated, "no date")):  # fmt: skip
            if isinstance(extra, FragmentYear) and (extra.with_region or extra.possible_deletion):
                rows.append(charts.YearRow(label=name, counts=_counts(extra), few=True))
    return _markup(charts.year_bars(rows, title=f"Outcome per {axis} year"))


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
    for oligo in result.assay.oligo_list:
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
    """Per tier, the closest primer site: fewest mismatches and gaps, then the longest clean 3'
    end (worst-case partial sites, without a full alignment, left out)."""
    best: dict[str, Any] = {}
    for s in sites:
        if s.role == "probe" or s.source == "blast_partial_worst_case" or not s.q_aln:
            continue
        key = (s.n_mismatch + s.n_gap, -s.clean_3prime_nt, s.id)
        if s.tier not in best or key < (
            best[s.tier].n_mismatch + best[s.tier].n_gap, -best[s.tier].clean_3prime_nt,
            best[s.tier].id,
        ):  # fmt: skip
            best[s.tier] = s
    return best


def site_glyphs(result: RunResult) -> dict[str, Markup]:
    """Per tier, the closest primer site as a glyph (P4)."""
    spec = result.specificity
    if spec is None:
        return {}
    out = {}
    for tier, s in closest_by_tier(spec.sites).items():
        label = (f"closest {s.role} site: {s.n_mismatch} mismatch(es), {s.n_gap} gap(s), "
                 f"{s.clean_3prime_nt} clean 3′ nt, {s.organism or 'unknown'}")  # fmt: skip
        svg = charts.site_glyph(s.q_aln, s.s_aln, 5, label)
        if svg:
            out[tier] = Markup(svg)  # noqa: S704 - SVG from alignment letters, label escaped
    return out
