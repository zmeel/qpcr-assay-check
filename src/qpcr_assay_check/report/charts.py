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


def coverage_steps(steps: list[tuple[str, int]], width: int = 230) -> str:
    """Aligned bars on one scale (not a funnel: funnel shapes distort widths): each step's count
    against the first."""
    if not steps or steps[0][1] <= 0:
        return ""
    top = steps[0][1]
    row = 13
    body: list[str] = []
    bar_w = width - 92
    for i, (name, n) in enumerate(steps):
        y = i * row
        w = bar_w * n / top
        body.append(
            f'<rect x="0" y="{y + 2}" width="{w:.1f}" height="{row - 4}" fill="#5B7C99">'
            f"<title>{escape(name)}: {n:,}</title></rect>"
            f'<text x="{bar_w + 4}" y="{y + 10}" fill="{INK}" font-size="9.5">{n:,} '
            f"{escape(name)}</text>"
        )
    label = "Coverage: " + "; ".join(f"{name} {n:,}" for name, n in steps)
    return _svg(width, row * len(steps), label, body, "fig steps")


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
        mid = (r.tm_min + r.tm_max) / 2
        fill = INK if r.primer else "#FFFFFF"
        if r.status == "FAIL":
            body.append(f'<path d="M{x(mid):.1f} {y - 4:.1f}l4 7h-8z" fill="{fill}" '
                        f'stroke="{INK}"><title>{title}, outside the limit</title>'
                        "</path>")  # fmt: skip
        else:
            body.append(f'<circle cx="{x(mid):.1f}" cy="{y:.1f}" r="3" fill="{fill}" '
                        f'stroke="{INK}"><title>{title}</title></circle>')  # fmt: skip
    for v in (lim[0], anneal, lim[1]):
        body.append(f'<text x="{x(v):.1f}" y="{h - 2}" text-anchor="middle" font-size="8.5" '
                    f'fill="{MUTED}">{v:g}</text>')  # fmt: skip
    label = (
        "Oligo Tm: "
        + "; ".join(
            f"{r.name} {r.tm_min:.1f}" + (f"–{r.tm_max:.1f}" if r.tm_max - r.tm_min >= 0.05 else "")
            for r in rows
        )
        + f" °C; primer preferred {pref[0]:g}–{pref[1]:g}, limit {lim[0]:g}–{lim[1]:g}, "
        f"annealing {anneal:g} °C"
    )
    return _svg(width, h, label, body, "fig tm")


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
    "tolerated": "#2F6FA8", "perfect": "#2F6FA8", "at_risk": "url(#q-risk)",
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


def site_glyph(q_aln: str, s_aln: str, tail: int, label: str) -> str:
    """One cell per oligo base: a match light, a mismatch black, an unread base (N) grey, a gap
    hatched; the primer 3' end underlined. The bases themselves are in the alignment tables."""
    cells = [(q, s) for q, s in zip(q_aln, s_aln, strict=False) if q != "-"]
    if not cells:
        return ""
    n, w = len(cells), 6
    body: list[str] = []
    for i, (q, s) in enumerate(cells):
        if s in "-.":
            fill = "url(#q-und)"
        elif s.upper() == "N":
            fill = "#A8B3BD"
        elif s.upper() != q.upper():
            fill = INK
        else:
            fill = "#E6EAEE"
        body.append(f'<rect x="{i * w}" y="0" width="{w - 1}" height="9" fill="{fill}"/>')
    if 0 < tail < n:
        body.append(f'<line x1="{(n - tail) * w}" x2="{n * w - 1}" y1="11" y2="11" stroke="{INK}" '
                    'stroke-width="1.2"/>')  # fmt: skip
    return _svg(n * w, 12, label, body, "fig glyph")
