"""Small inline-SVG figures for the report (report review 2026-11-20).

Pure functions: plain numbers in, an SVG string out. No JavaScript, no plotting library, fixed
precision and sorted input, so the same inputs give the same bytes. Every figure repeats numbers
that are also in a table of the report or the workbook; none is the only place a value lives.

Classes are told apart by fill *and* texture, so they read in greyscale and for colour-blind
readers: detectable a solid blue; at risk amber with a diagonal hatch; likely failure red with a
cross-hatch; a possible deletion (region missing where it should be) dark red, cross-hatched;
undetermined white with grey dots and an outline. Order is always detectable, at risk, likely
failure, region missing, undetermined.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape

FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif"
INK, MUTED, RULE = "#17222D", "#55636F", "#D3DBE2"

#: class -> (fill, legend label)
CLASSES: dict[str, tuple[str, str]] = {
    "detectable": ("#2F6FA8", "detectable"),
    "at_risk": ("url(#q-risk)", "at risk"),
    "likely_failure": ("url(#q-fail)", "likely failure"),
    "deleted": ("url(#q-del)", "region missing"),
    "undetermined": ("url(#q-und)", "undetermined"),
}
ORDER = ("detectable", "at_risk", "likely_failure", "deleted", "undetermined")


def defs() -> str:
    """The patterns every figure refers to: one hidden SVG near the top of the page."""
    return (
        '<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">'
        "<defs>"
        '<pattern id="q-risk" width="6" height="6" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(45)"><rect width="6" height="6" fill="#E0A526"/>'
        '<line x1="0" y1="0" x2="0" y2="6" stroke="#7A5200" stroke-width="2"/></pattern>'
        '<pattern id="q-fail" width="6" height="6" patternUnits="userSpaceOnUse">'
        '<rect width="6" height="6" fill="#B8322F"/>'
        '<path d="M0 0L6 6M6 0L0 6" stroke="#FFFFFF" stroke-width="1"/></pattern>'
        '<pattern id="q-del" width="6" height="6" patternUnits="userSpaceOnUse">'
        '<rect width="6" height="6" fill="#6E1E1C"/>'
        '<path d="M0 3H6M3 0V6" stroke="#FFFFFF" stroke-width="1"/></pattern>'
        '<pattern id="q-und" width="6" height="6" patternUnits="userSpaceOnUse">'
        '<rect width="6" height="6" fill="#FFFFFF"/>'
        '<circle cx="3" cy="3" r="1.1" fill="#8A97A3"/></pattern>'
        # the site-level zones of the off-target map: light, so the marks stay legible
        '<pattern id="z-crit" width="7" height="7" patternUnits="userSpaceOnUse">'
        '<rect width="7" height="7" fill="#F6DCDA"/>'
        '<path d="M0 0L7 7M7 0L0 7" stroke="#D9A3A0" stroke-width="0.7"/></pattern>'
        '<pattern id="z-warn" width="7" height="7" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(45)"><rect width="7" height="7" fill="#FBF0D6"/>'
        '<line x1="0" y1="0" x2="0" y2="7" stroke="#E3C98A" stroke-width="0.8"/></pattern>'
        "</defs></svg>"
    )


def _svg(w: float, h: float, label: str, body: list[str], css: str = "fig") -> str:
    return (
        f'<svg class="{css}" viewBox="0 0 {w:g} {h:g}" width="{w:g}" height="{h:g}" '
        f'role="img" aria-label="{escape(label)}" font-family="{FONT}" font-size="11">'
        f"<title>{escape(label)}</title>" + "".join(body) + "</svg>"
    )


def _seg(x: float, y: float, w: float, h: float, cls: str, title: str) -> str:
    fill = CLASSES[cls][0]
    stroke = ' stroke="#8A97A3" stroke-width="0.8"' if cls == "undetermined" else ""
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"{stroke}>'
        f"<title>{escape(title)}</title></rect>"
    )


def legend(classes: list[str], x: float = 0, y: float = 0) -> str:
    """One row of swatches with their labels."""
    out, cx = [], x
    for cls in classes:
        out.append(_seg(cx, y, 10, 10, cls, CLASSES[cls][1]))
        out.append(f'<text x="{cx + 14:.1f}" y="{y + 9:.1f}" fill="{INK}">{CLASSES[cls][1]}</text>')
        cx += 22 + 6.2 * len(CLASSES[cls][1])
    return "".join(out)


@dataclass
class Counts:
    """Genomes per outcome class (``deleted``: region missing where it should be)."""

    detectable: int = 0
    at_risk: int = 0
    likely_failure: int = 0
    deleted: int = 0
    undetermined: int = 0

    def get(self, cls: str) -> int:
        return int(getattr(self, cls))

    @property
    def judged(self) -> int:
        """The base of the status percentage: undetermined genomes left out."""
        return self.detectable + self.at_risk + self.likely_failure + self.deleted

    @property
    def total(self) -> int:
        return self.judged + self.undetermined


def _note(c: Counts) -> str:
    parts = [f"{c.get(k):,} {CLASSES[k][1]}" for k in ORDER[1:] if c.get(k)]
    return " · ".join(parts)


def window_meter(c: Counts, warn_pct: float, fail_pct: float, width: int = 230) -> str:
    """One bar for the pooled status window, its base the judged genomes (undetermined left
    out, as in the status), with the configured limits as ticks; the undetermined count is
    printed beside it, never hidden."""
    h, bar_y, bar_h = 34, 4, 14
    body: list[str] = []
    if c.judged:
        x = 0.0
        for cls in ORDER[:4]:
            n = c.get(cls)
            if n:
                w = width * n / c.judged
                body.append(_seg(x, bar_y, w, bar_h, cls, f"{CLASSES[cls][1]}: {n:,}"))
                x += w
    else:
        body.append(f'<rect x="0" y="{bar_y}" width="{width}" height="{bar_h}" fill="none" '
                    f'stroke="{RULE}"/>')  # fmt: skip
    for pct in (warn_pct, fail_pct):
        tx = width * pct / 100
        body.append(
            f'<line x1="{tx:.1f}" x2="{tx:.1f}" y1="1" y2="{bar_y + bar_h + 3}" stroke="{INK}" '
            f'stroke-width="1.2"/><text x="{tx:.1f}" y="{h - 2}" text-anchor="middle" '
            f'font-size="9" fill="{INK}">{pct:g}%</text>'
        )
    share = f"{100 * c.detectable / c.judged:.1f}% detectable" if c.judged else "none judged"
    label = (f"Status window: {share} of {c.judged:,} judged; {c.undetermined:,} undetermined; "
             f"limits {warn_pct:g}% (Review) and {fail_pct:g}% (Exceeds limit)")  # fmt: skip
    return _svg(width, h, label, body, "fig meter")


def coverage_steps(
    steps: list[tuple[str, int]], window: tuple[str, int] | None = None, width: int = 240
) -> str:
    """Aligned bars on one scale (not a funnel: funnel shapes distort widths): each step's count
    against the first. ``window``, the records of the status window, is a filter of another
    kind (a time span, not records lost along the way), so it is drawn apart, hatched, below a
    gap (report review 2026-11-25, third round)."""
    if not steps or steps[0][1] <= 0:
        return ""
    top = steps[0][1]
    row = 13
    body: list[str] = []
    bar_w = width - 118
    for i, (name, n) in enumerate(steps):
        y = i * row
        w = bar_w * n / top
        body.append(
            f'<rect x="0" y="{y + 2}" width="{w:.1f}" height="{row - 4}" fill="#5B7C99">'
            f"<title>{escape(name)}: {n:,}</title></rect>"
            f'<text x="{bar_w + 4}" y="{y + 10}" fill="{INK}" font-size="9.5">{n:,} '
            f"{escape(name)}</text>"
        )
    h = row * len(steps)
    if window is not None:
        name, n = window
        y = h + 4
        w = bar_w * n / top
        body.append(
            f'<rect x="0" y="{y + 2}" width="{w:.1f}" height="{row - 4}" fill="url(#q-risk)" '
            f'stroke="#5B7C99" stroke-width="0.8"><title>{escape(name)}: {n:,}</title></rect>'
            f'<text x="{bar_w + 4}" y="{y + 10}" fill="{INK}" font-size="9.5">{n:,} '
            f"{escape(name)}</text>"
        )
        h = y + row
    label = "Coverage: " + "; ".join(
        f"{name} {n:,}" for name, n in [*steps, *([window] if window else [])]
    )
    return _svg(width, h, label, body, "fig steps")


@dataclass
class TmRow:
    name: str
    tm_min: float
    tm_max: float
    status: str  # PASS | WARN | FAIL (of the Tm check)
    primer: bool = True


def tm_strip(
    rows: list[TmRow],
    pref: tuple[float, float],
    lim: tuple[float, float],
    anneal: float,
    width: int = 240,
) -> str:
    """A dot (or a range, for a degenerate oligo) per oligo on a Tm axis, against the primer
    preferred band (shaded) and limits (lines), with the annealing temperature dashed. Tm has
    no true zero, so bars from an axis floor would mean nothing as lengths. An oligo whose Tm
    check is outside the limit gets a triangle. Probes are drawn hollow: the primer bands do
    not apply to them."""
    if not rows:
        return ""
    lo = min([r.tm_min for r in rows] + [lim[0], anneal]) - 2
    hi = max([r.tm_max for r in rows] + [lim[1]]) + 2
    left, row = max(64, 6 + 6 * max(len(r.name) for r in rows)), 15
    width = max(width, left + 160)

    def x(v: float) -> float:
        return left + (width - left - 6) * (v - lo) / (hi - lo)

    h = row * len(rows) + 14
    body = [
        f'<rect x="{x(pref[0]):.1f}" y="0" width="{x(pref[1]) - x(pref[0]):.1f}" '
        f'height="{h - 12}" fill="#DCE7F2"><title>primer preferred {pref[0]:g}-{pref[1]:g} °C'
        "</title></rect>"
    ]
    for v in lim:
        body.append(f'<line x1="{x(v):.1f}" x2="{x(v):.1f}" y1="0" y2="{h - 12}" stroke="{INK}" '
                    'stroke-width="1"/>')  # fmt: skip
    body.append(f'<line x1="{x(anneal):.1f}" x2="{x(anneal):.1f}" y1="0" y2="{h - 12}" '
                f'stroke="{MUTED}" stroke-dasharray="3 2"/>')  # fmt: skip
    for i, r in enumerate(rows):
        y = i * row + row / 2
        name = escape(r.name)
        tm = f"{r.tm_min:.1f}" if r.tm_max - r.tm_min < 0.05 else f"{r.tm_min:.1f}–{r.tm_max:.1f}"
        title = f"{escape(r.name)}: Tm {tm} °C"
        body.append(f'<text x="0" y="{y + 3.5:.1f}" font-size="10" fill="{INK}">{name}</text>')
        if r.tm_max - r.tm_min >= 0.05:
            body.append(f'<line x1="{x(r.tm_min):.1f}" x2="{x(r.tm_max):.1f}" y1="{y:.1f}" '
                        f'y2="{y:.1f}" stroke="{INK}" stroke-width="2"/>')  # fmt: skip
        # the mark sits where the check is decided: at the worst variant when a range crosses a
        # bound (report review 2026-11-25, third round: the midpoint sat on the limit line)
        mid = (r.tm_min + r.tm_max) / 2
        bound = lim if r.status == "FAIL" else pref
        if r.primer and r.status in ("FAIL", "WARN"):
            over, under = r.tm_max - bound[1], bound[0] - r.tm_min
            if over > 0 or under > 0:
                mid = r.tm_max if over >= under else r.tm_min
        fill = INK if r.primer else "#FFFFFF"
        if r.status == "FAIL":
            body.append(f'<path d="M{x(mid):.1f} {y - 4:.1f}l4 7h-8z" fill="{fill}" '
                        f'stroke="{INK}"><title>{title}, outside the limit (worst variant '
                        f"{mid:.1f} °C)</title></path>")  # fmt: skip
        else:
            body.append(f'<circle cx="{x(mid):.1f}" cy="{y:.1f}" r="3" fill="{fill}" '
                        f'stroke="{INK}"><title>{title}</title></circle>')  # fmt: skip
    for v in (lim[0], anneal, lim[1]):
        body.append(f'<text x="{x(v):.1f}" y="{h - 2}" text-anchor="middle" font-size="8.5" '
                    f'fill="{MUTED}">{v:g}</text>')  # fmt: skip
    # the bands named in the figure itself (third report review): limits and preferred range
    centre = (x(pref[0]) + x(pref[1])) / 2
    body.append(f'<text x="{centre:.1f}" y="-3" text-anchor="middle" font-size="8" '
                f'fill="{MUTED}">preferred {pref[0]:g}–{pref[1]:g}</text>')  # fmt: skip
    for v in lim:
        body.append(f'<text x="{x(v):.1f}" y="-3" text-anchor="middle" font-size="8" '
                    f'fill="{MUTED}">limit</text>')  # fmt: skip
    label = (
        "Oligo Tm: "
        + "; ".join(
            f"{r.name} {r.tm_min:.1f}" + (f"–{r.tm_max:.1f}" if r.tm_max - r.tm_min >= 0.05 else "")
            for r in rows
        )
        + f" °C; primer preferred {pref[0]:g}–{pref[1]:g}, limit {lim[0]:g}–{lim[1]:g}, "
        f"annealing {anneal:g} °C"
    )
    # a 10 px band on top for the band names
    return _svg(width, h + 10, label, ['<g transform="translate(0 10)">', *body, "</g>"], "fig tm")


@dataclass
class YearRow:
    label: str
    counts: Counts
    in_window: bool = False
    few: bool = False


def year_bars(rows: list[YearRow], width: int = 640, title: str = "") -> str:
    """One 100% bar per year, split into the outcome classes, its count and named problem
    classes printed beside it; the status window bracketed; years with few judged genomes drawn
    pale and labelled. Undetermined genomes are a segment of their own, never hidden."""
    if not rows:
        return ""
    row, left, right = 16, 104, 190
    bar_w = width - left - right
    top = 18
    body = [legend(list(ORDER), left, 0)]
    for i, r in enumerate(rows):
        y = top + i * row
        c = r.counts
        op = ' opacity="0.45"' if r.few else ""
        body.append(f'<text x="{left - 6}" y="{y + 11}" text-anchor="end" fill="{INK}">'
                    f"{escape(r.label)}</text><g{op}>")  # fmt: skip
        x = float(left)
        for cls in ORDER:
            n = c.get(cls)
            if n and c.total:
                w = bar_w * n / c.total
                body.append(_seg(x, y + 2, w, row - 4, cls, f"{r.label}: {CLASSES[cls][1]} {n:,}"))
                x += w
        if not c.total:
            body.append(f'<rect x="{left}" y="{y + 2}" width="{bar_w}" height="{row - 4}" '
                        f'fill="none" stroke="{RULE}"/>')  # fmt: skip
        body.append("</g>")
        text = f"{c.total:,}"
        note = _note(c)
        if note:
            text += f" · {note}"
        if r.few:
            text += " · few records"
        body.append(f'<text x="{left + bar_w + 6}" y="{y + 11}" fill="{INK}">{escape(text)}</text>')
    win = [i for i, r in enumerate(rows) if r.in_window]
    if win:
        y0, y1 = top + win[0] * row + 1, top + (win[-1] + 1) * row - 1
        body.append(f'<path d="M58 {y0}h-4V{y1}h4" fill="none" stroke="{INK}" stroke-width="1.2"/>'
                    f'<text x="50" y="{(y0 + y1) / 2 + 3:.1f}" text-anchor="end" font-size="9" '
                    f'fill="{INK}">window</text>')  # fmt: skip
    label = title or "Outcome per year"
    label += ": " + "; ".join(
        f"{r.label} {r.counts.total:,}" + (f" ({_note(r.counts)})" if _note(r.counts) else "")
        for r in rows
    )
    return _svg(width, top + row * len(rows) + 2, label, body, "fig years")


@dataclass
class SiteColumn:
    """Genomes with a mismatch at one oligo base, by the class of the whole site."""

    by_class: dict[str, int] = field(default_factory=dict)
    gaps: int = 0

    @property
    def total(self) -> int:
        return sum(self.by_class.values())


_SITE_FILL = {
    "tolerated": "#2F6FA8", "at_risk": "url(#q-risk)",
    "likely_failure": "url(#q-fail)", "indeterminate": "url(#q-und)",
}  # fmt: skip
_SITE_ORDER = ("tolerated", "at_risk", "likely_failure", "indeterminate")


def site_map(
    name: str, oligo: str, judged: int, columns: dict[int, SiteColumn], tail: int, width: int = 640
) -> str:
    """Where the target genomes differ from one oligo: one column per base (5'->3'), its height
    the share of judged genomes with a mismatch there on a linear 0-100% scale, split by the class
    of the whole site (not the effect of that one base), the genome count above every non-zero
    column, gaps as a tick below the axis, the primer 3' end (last ``tail`` bases) bracketed."""
    n = len(oligo)
    if not n or judged <= 0:
        return ""
    left, plot_h, top = 30, 30, 24
    col = min(12.0, (width - left - 8) / n)
    body: list[str] = [
        f'<line x1="{left}" x2="{left + col * n:.1f}" y1="{top + plot_h}" y2="{top + plot_h}" '
        f'stroke="{INK}" stroke-width="0.8"/>',
        f'<text x="{left - 4}" y="{top + 4}" text-anchor="end" font-size="8.5" fill="{MUTED}">'
        "100%</text>",
        f'<text x="{left - 4}" y="{top + plot_h}" text-anchor="end" font-size="8.5" '
        f'fill="{MUTED}">0</text>',
    ]
    for i in range(n):
        cx = left + i * col
        c = columns.get(i)
        if c and c.total:
            y = top + plot_h
            for cls in _SITE_ORDER:
                k = c.by_class.get(cls, 0)
                if not k:
                    continue
                hgt = max(1.0, plot_h * k / judged)
                y -= hgt
                stroke = ' stroke="#8A97A3" stroke-width="0.6"' if cls == "indeterminate" else ""
                body.append(
                    f'<rect x="{cx + 1:.1f}" y="{y:.1f}" width="{col - 2:.1f}" height="{hgt:.1f}" '
                    f'fill="{_SITE_FILL[cls]}"{stroke}><title>{escape(name)} base {i + 1} '
                    f"(-{n - i} from the 3′ end): {k:,} genome(s), site {cls.replace('_', ' ')}"
                    "</title></rect>"
                )
            body.append(f'<text x="{cx + col / 2:.1f}" y="{y - 2:.1f}" text-anchor="middle" '
                        f'font-size="8.5" fill="{INK}">{c.total:,}</text>')  # fmt: skip
        if c and c.gaps:
            body.append(f'<line x1="{cx + 2:.1f}" x2="{cx + col - 2:.1f}" y1="{top + plot_h + 4}" '
                        f'y2="{top + plot_h + 4}" stroke="{INK}" stroke-width="2.5">'
                        f"<title>{c.gaps:,} genome(s) with a gap at base {i + 1}</title>"
                        "</line>")  # fmt: skip
        body.append(
            f'<text x="{cx + col / 2:.1f}" y="{top + plot_h + 15}" text-anchor="middle" '
            f'font-family="ui-monospace, Menlo, Consolas, monospace" font-size="10" '
            f'fill="{INK}">{escape(oligo[i])}</text>'
        )
    if 0 < tail < n:
        x0 = left + (n - tail) * col
        body.append(f'<path d="M{x0:.1f} {top + plot_h + 20}v3H{left + n * col:.1f}v-3" '
                    f'fill="none" stroke="{INK}" stroke-width="1"/>'
                    f'<text x="{left + n * col + 3:.1f}" y="{top + plot_h + 24}" font-size="8.5" '
                    f'fill="{INK}">3′</text>')  # fmt: skip
    body.append(f'<text x="0" y="11" font-size="11" font-weight="600" fill="{INK}">'
                f"{escape(name)}</text>")  # fmt: skip
    label = f"{name}: genomes with a mismatch per base, of {judged:,} judged: " + (
        "; ".join(f"base {i + 1} {columns[i].total:,}" for i in sorted(columns) if columns[i].total)
        or "none"
    )
    return _svg(left + n * col + 16, top + plot_h + 28, label, body, "fig sitemap")


# ---------------------------------------------------------------- off-target site levels
LEVEL_FILL = {"critical": "#8E2422", "warning": "#D9A21B", "minor": "#FFFFFF"}
TIER_SHAPE = {"near_neighbours": "diamond", "background": "square", "exclusivity": "circle",
              "out_of_scope": "triangle"}  # fmt: skip


@dataclass
class MapPoint:
    """One organism's closest primer site in one tier."""

    label: str
    tier: str
    mismatches: int
    clean3: int
    gaps: int
    level: str  # the site's own level: the zones show the count limits, the fill the outcome
    title: str
    number: int = 0  # its row in the table under the figure


@dataclass
class Zones:
    """The primer-site levels' count limits (``specificity.primer_site``)."""

    crit_mm: int
    crit_gaps: int
    crit_clean: int
    warn_mm: int
    warn_gaps: int
    warn_clean: int


def _mark(shape: str, x: float, y: float, fill: str, title: str, r: float = 4.5) -> str:
    t = f"<title>{escape(title)}</title>"
    st = f'fill="{fill}" stroke="{INK}" stroke-width="1.2"'
    k = r + 1
    if shape == "diamond":
        return f'<path d="M{x:.1f} {y - k:.1f}l{k} {k}l-{k} {k}l-{k} -{k}z" {st}>{t}</path>'
    if shape == "square":
        d = 2 * r
        return f'<rect x="{x - r:.1f}" y="{y - r:.1f}" width="{d}" height="{d}" {st}>{t}</rect>'
    if shape == "triangle":
        return f'<path d="M{x:.1f} {y - r - 1:.1f}l{r + 1} {2 * r}h-{2 * r + 2}z" {st}>{t}</path>'
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" {st}>{t}</circle>'


def site_level_map(points: list[MapPoint], zones: Zones, top_clean: int, width: int = 900) -> str:
    """Each organism's closest primer site placed by its mismatches (x) and clean 3' end (y)
    on the zones of the critical and warning levels; the tier is the shape, the site's own level
    the fill (the R1-R9 classes can move a site out of the zone its counts put it in). Sites
    with more gaps than the warning level allows stand in a column of their own. One mark per
    organism: database redundancy does not weigh (third report review, 2026-11-25). Each mark
    carries the number of its organism in the table under the figure (user, 2026-11-26: names
    beside the marks ran into each other)."""
    if not points:
        return ""
    left, top, ph, cw = 56, 40, 300, 88
    gap_x = left + cw * 7 + 70
    top_clean = max(top_clean, 6)

    def x_of(p: MapPoint) -> float:
        return gap_x if p.gaps > zones.warn_gaps else left + cw * (min(p.mismatches, 6) + 0.5)

    def y_of(c: float) -> float:
        return top + ph * (1 - c / top_clean)

    b = [
        f'<rect x="{left}" y="{y_of(top_clean):.1f}" width="{cw * (zones.warn_mm + 1)}" '
        f'height="{y_of(zones.warn_clean - 0.5) - y_of(top_clean):.1f}" fill="url(#z-warn)">'
        f"<title>warning: up to {zones.warn_mm} mismatches, up to {zones.warn_gaps} gap(s), at "
        f"least {zones.warn_clean} clean 3′ nt</title></rect>",
        f'<rect x="{left}" y="{y_of(top_clean):.1f}" width="{cw * (zones.crit_mm + 1)}" '
        f'height="{y_of(zones.crit_clean - 0.5) - y_of(top_clean):.1f}" fill="url(#z-crit)">'
        f"<title>critical: up to {zones.crit_mm} mismatches, {zones.crit_gaps} gap(s), at least "
        f"{zones.crit_clean} clean 3′ nt</title></rect>",
        f'<rect x="{gap_x - 50}" y="{y_of(top_clean):.1f}" width="100" '
        f'height="{y_of(0) - y_of(top_clean) + 8:.1f}" fill="#F2F4F6"/>',
        f'<text x="{left + 4}" y="{top - 22}" font-size="12" font-weight="600" fill="#8E2422">'
        f"critical zone: ≤{zones.crit_mm} mismatches, {zones.crit_gaps} gap, ≥{zones.crit_clean} "
        "clean 3′ nt</text>",
        f'<text x="{left + cw * (zones.crit_mm + 1) + 4}" y="{top - 6}" font-size="12" '
        f'font-weight="600" fill="#6B4A00">warning zone: ≤{zones.warn_mm} mismatches, '
        f"≤{zones.warn_gaps} gap, ≥{zones.warn_clean} clean 3′ nt</text>",
        f'<text x="{gap_x}" y="{top - 6}" font-size="12" text-anchor="middle" fill="{MUTED}">'
        f"&gt;{zones.warn_gaps} gap{'s' if zones.warn_gaps != 1 else ''}</text>",
    ]
    y0 = y_of(0) + 10
    b.append(f'<line x1="{left}" x2="{gap_x + 50}" y1="{y0:.1f}" y2="{y0:.1f}" stroke="{INK}"/>')
    for mm in range(7):
        b.append(f'<text x="{left + cw * (mm + 0.5):.1f}" y="{y0 + 16:.1f}" font-size="12" '
                 f'text-anchor="middle" fill="{MUTED}">'
                 f'{mm if mm < 6 else "6+"}</text>')  # fmt: skip
    b.append(f'<text x="{left + cw * 3.5:.1f}" y="{y0 + 34:.1f}" font-size="12" '
             f'text-anchor="middle" fill="{MUTED}">mismatches of the closest primer site '
             "(0 = binds perfectly)</text>")  # fmt: skip
    step = 5 if top_clean <= 30 else 10
    for c in range(0, top_clean + 1, step):
        b.append(f'<text x="{left - 6}" y="{y_of(c) + 4:.1f}" font-size="12" text-anchor="end" '
                 f'fill="{MUTED}">{c}</text><line x1="{left}" x2="{left + cw * 7}" '
                 f'y1="{y_of(c):.1f}" y2="{y_of(c):.1f}" stroke="{RULE}" '
                 'stroke-width="0.5"/>')  # fmt: skip
    mid = y_of(top_clean / 2)
    b.append(f'<text x="14" y="{mid:.1f}" font-size="12" fill="{MUTED}" text-anchor="middle" '
             f'transform="rotate(-90 14 {mid:.1f})">clean 3′ nt (matched run at the 3′ end)'
             "</text>")  # fmt: skip
    # one mark per position; organisms at the same spot share it, their numbers beside it
    spots: dict[tuple[float, float], list[MapPoint]] = {}
    for p in points:
        spots.setdefault((round(x_of(p), 1), round(y_of(min(p.clean3, top_clean)), 1)), []).append(
            p
        )
    placed: dict[float, list[float]] = {}
    for (x, y), ps in sorted(spots.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        p = min(ps, key=lambda q: ("critical", "warning", "minor").index(q.level))
        b.append(_mark(TIER_SHAPE.get(p.tier, "circle"), x, y, LEVEL_FILL.get(p.level, "#FFFFFF"),
                       "; ".join(f"{q.number}. {q.title}" for q in ps), 6))  # fmt: skip
        ly = y + 4.5
        for other in placed.get(x, []):  # number labels of one column kept 15 px apart
            if abs(other - ly) < 15:
                ly = other + 15
        placed.setdefault(x, []).append(ly)
        nums = ", ".join(str(q.number) for q in sorted(ps, key=lambda q: q.number))
        b.append(f'<text x="{x + 10:.1f}" y="{ly:.1f}" font-size="12.5" font-weight="600" '
                 f'fill="{INK}">{escape(nums)}</text>')  # fmt: skip
    # key: shape = tier, fill = level
    kx, ky = gap_x + 66, top + 4
    b.append(f'<text x="{kx}" y="{ky}" font-size="12" fill="{MUTED}">shape: tier</text>')
    for i, (tier, name) in enumerate((("near_neighbours", "near neighbours"),
                                      ("background", "background"),
                                      ("exclusivity", "clinical list"))):  # fmt: skip
        b.append(_mark(TIER_SHAPE[tier], kx + 6, ky + 16 + 18 * i, INK, name, 5)
                 + f'<text x="{kx + 17}" y="{ky + 20 + 18 * i}" font-size="12" fill="{INK}">'
                 f"{name}</text>")  # fmt: skip
    b.append(f'<text x="{kx}" y="{ky + 82}" font-size="12" fill="{MUTED}">fill: its level</text>')
    for i, lvl in enumerate(("critical", "warning", "minor")):
        b.append(_mark("circle", kx + 6, ky + 98 + 18 * i, LEVEL_FILL[lvl], lvl, 5)
                 + f'<text x="{kx + 17}" y="{ky + 102 + 18 * i}" font-size="12" fill="{INK}">'
                 f"{lvl}</text>")  # fmt: skip
    label = "Closest primer site per off-target organism: " + "; ".join(
        f"{p.number}. {p.label} ({p.tier}) {p.mismatches} mm, {p.gaps} gap(s), {p.clean3} clean "
        f"3′, {p.level}"
        for p in points
    )
    return _svg(max(width, kx + 120), y0 + 44, label, b, "fig levels")


def site_dot(p: MapPoint, zones: Zones, top_clean: int) -> str:
    """Part A's small version: one tier's closest primer site on the zones, mm and clean 3'
    printed beside it (third report review: in the cell glyph a perfect match was the emptiest
    picture)."""
    cw, w, h = 13, 91, 30
    top_clean = max(top_clean, 6)

    def y_of(c: float) -> float:
        return 2 + (h - 4) * (1 - min(c, top_clean) / top_clean)

    x = 2 + cw * (min(p.mismatches, 6) + 0.5)
    body = [
        f'<rect x="2" y="2" width="{cw * (zones.warn_mm + 1)}" '
        f'height="{y_of(zones.warn_clean - 0.5) - 2:.1f}" fill="url(#z-warn)"/>',
        f'<rect x="2" y="2" width="{cw * (zones.crit_mm + 1)}" '
        f'height="{y_of(zones.crit_clean - 0.5) - 2:.1f}" fill="url(#z-crit)"/>',
        f'<rect x="2" y="2" width="{w}" height="{h - 4}" fill="none" stroke="{RULE}"/>',
        _mark("circle", x, y_of(p.clean3), LEVEL_FILL.get(p.level, "#FFFFFF"), p.title, 3.5),
        f'<text x="{w + 8}" y="13" font-size="9.5" font-weight="600" fill="{INK}">'
        f"{p.mismatches} mm{f', {p.gaps} gap' if p.gaps else ''}</text>",
        f'<text x="{w + 8}" y="25" font-size="9" fill="{INK}">{p.clean3} clean 3′</text>',
    ]
    return _svg(w + 70, h, p.title, body, "fig dot")


@dataclass
class StructRow:
    """One hairpin or dimer: its worst Tm (None: no structure; below 0: too weak to matter)."""

    group: str
    label: str
    tm: float | None
    status: str  # PASS | WARN | FAIL
    found: bool = True


def structure_strip(rows: list[StructRow], warn_tm: float, fail_tm: float, width: int = 900) -> str:
    """Each hairpin and dimer as a dot on a Tm axis against the review zone (from ``warn_tm``)
    and the limit zone (from ``fail_tm``, the annealing temperature by default); a flagged one is
    a triangle. "none" and "< 0" stand in a gutter, not plotted as 0 °C (third report review,
    2026-11-25, M5: fourteen of fifteen table rows said "within")."""
    if not rows:
        return ""
    row, gutter = 21, 64
    left = 104 + int(7.0 * max(len(r.label) for r in rows))
    x0 = left + gutter
    hi = max([fail_tm + 5] + [r.tm + 4 for r in rows if r.tm is not None])
    plot = width - x0 - 30

    def x(v: float) -> float:
        return x0 + plot * max(0.0, v) / hi

    top = 20
    h = top + row * len(rows)
    body = [
        f'<rect x="{x(warn_tm):.1f}" y="{top}" width="{x(fail_tm) - x(warn_tm):.1f}" '
        f'height="{h - top}" fill="url(#z-warn)"><title>outside preferred from {warn_tm:g} °C'
        "</title></rect>",
        f'<rect x="{x(fail_tm):.1f}" y="{top}" width="{x(hi) - x(fail_tm):.1f}" '
        f'height="{h - top}" fill="url(#z-crit)"><title>outside the limit from {fail_tm:g} °C'
        "</title></rect>",
        f'<text x="{x(warn_tm) + 2:.1f}" y="14" font-size="12" fill="#6B4A00">≥{warn_tm:g} °C '
        "review</text>",
        f'<text x="{x(fail_tm) + 2:.1f}" y="14" font-size="12" fill="#8E2422">'
        f"≥{fail_tm:g} °C</text>",
        f'<text x="{left + gutter / 2:.1f}" y="14" font-size="12" text-anchor="middle" '
        f'fill="{MUTED}">none / &lt;0</text>',
    ]
    last = ""
    for i, r in enumerate(rows):
        y = top + i * row + row / 2
        if r.group != last:
            body.append(f'<text x="0" y="{y + 4.5:.1f}" font-size="12.5" fill="{MUTED}">'
                        f"{escape(r.group)}</text>")  # fmt: skip
            if i:
                body.append(f'<line x1="0" x2="{width - 30}" y1="{y - row / 2:.1f}" '
                            f'y2="{y - row / 2:.1f}" stroke="{RULE}" '
                            'stroke-width="0.5"/>')  # fmt: skip
            last = r.group
        body.append(f'<text x="96" y="{y + 4.5:.1f}" font-size="12.5" fill="{INK}">'
                    f"{escape(r.label)}</text>")  # fmt: skip
        title = f"{r.group} {r.label}: " + (
            "no structure" if not r.found or r.tm is None else f"Tm {r.tm:.1f} °C"
        )
        if not r.found or r.tm is None or r.tm < 0:
            body.append(f'<text x="{left + gutter / 2:.1f}" y="{y + 4.5:.1f}" font-size="12" '
                        f'text-anchor="middle" fill="{MUTED}">'
                        f"{'none' if not r.found or r.tm is None else '&lt;0'}"
                        f"<title>{escape(title)}</title></text>")  # fmt: skip
            continue
        body.append(f'<line x1="{x0}" x2="{x(r.tm):.1f}" y1="{y:.1f}" y2="{y:.1f}" '
                    f'stroke="{RULE}" stroke-width="1"/>')  # fmt: skip
        if r.status in ("WARN", "FAIL"):
            body.append(f'<path d="M{x(r.tm):.1f} {y - 7:.1f}l7 11h-14z" fill="{INK}">'
                        f"<title>{escape(title)}, flagged</title></path>")  # fmt: skip
        else:
            body.append(f'<circle cx="{x(r.tm):.1f}" cy="{y:.1f}" r="4.5" fill="{INK}">'
                        f"<title>{escape(title)}</title></circle>")  # fmt: skip
        body.append(f'<text x="{x(r.tm) + 10:.1f}" y="{y + 4.5:.1f}" font-size="12" fill="{INK}">'
                    f"{r.tm:.1f}</text>")  # fmt: skip
    y1 = h + 2
    body.append(f'<line x1="{x0}" x2="{x(hi):.1f}" y1="{y1}" y2="{y1}" stroke="{INK}"/>')
    for v in range(0, int(hi) + 1, 10):
        body.append(f'<text x="{x(v):.1f}" y="{y1 + 15}" font-size="12" text-anchor="middle" '
                    f'fill="{MUTED}">{v}</text>')  # fmt: skip
    body.append(f'<text x="{x0 + plot / 2:.1f}" y="{y1 + 31}" font-size="12" text-anchor="middle" '
                f'fill="{MUTED}">structure Tm (°C), worst degenerate variant; '
                "▲ flagged</text>")  # fmt: skip
    label = "Hairpins and dimers, Tm: " + "; ".join(
        f"{r.group} {r.label} " + ("none" if not r.found or r.tm is None else f"{r.tm:.1f} °C")
        for r in rows
    )
    return _svg(width, y1 + 36, label, body, "fig structs")


@dataclass
class AcctBar:
    """One 100% bar of an accounting figure: its segments (fill, count, name) and its note."""

    label: str
    segments: list[tuple[str, int, str]]
    note: str
    gap_before: bool = False


def accounting(bars: list[AcctBar], width: int = 640) -> str:
    """Aligned 100% bars, each with its counts printed beside it: where every listed record
    went, then per oligo and for the whole fragment the genomes with a detectable copy (third
    report review, 2026-11-25, M6). A segment of 0 is not drawn; its count stays in the note."""
    bars = [b for b in bars if sum(n for _f, n, _t in b.segments) > 0]
    if not bars:
        return ""
    row, left = 17, 8 + int(5.8 * max(len(b.label) for b in bars))
    right = 8 + int(5.4 * max(len(b.note) for b in bars))
    bar_w = max(120, width - left - right)
    width = left + bar_w + right
    body: list[str] = []
    y = 0.0
    for b in bars:
        if b.gap_before:
            y += 8
        total = sum(n for _f, n, _t in b.segments)
        body.append(f'<text x="{left - 6}" y="{y + 12:.1f}" text-anchor="end" font-size="10" '
                    f'fill="{INK}">{escape(b.label)}</text>')  # fmt: skip
        x = float(left)
        for fill, n, name in b.segments:
            if n <= 0:
                continue
            w = bar_w * n / total
            light = fill.startswith("url(#q-und") or fill == "#FFFFFF"
            stroke = ' stroke="#8A97A3" stroke-width="0.8"' if light else ""
            body.append(f'<rect x="{x:.1f}" y="{y + 3:.1f}" width="{w:.1f}" height="{row - 6}" '
                        f'fill="{fill}"{stroke}><title>{escape(b.label)}: {escape(name)} '
                        f"{n:,}</title></rect>")  # fmt: skip
            x += w
        body.append(f'<text x="{left + bar_w + 6}" y="{y + 12:.1f}" font-size="9.5" '
                    f'fill="{INK}">{escape(b.note)}</text>')  # fmt: skip
        y += row
    label = "Coverage and copies: " + "; ".join(f"{b.label}: {b.note}" for b in bars)
    return _svg(width, y + 2, label, body, "fig acct")
