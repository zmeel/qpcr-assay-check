"""Charts for the report as inline SVG (no JavaScript library, no CDN).

The report used an interactive Plotly chart until 2026-09-25; the inlined Plotly bundle made
every report about 5 MB for one bar chart (user: report size), so the chart is drawn as SVG.
"""

from __future__ import annotations

from html import escape

from ..config import Config
from ..results import RunResult

_W, _H = 640, 300  # viewBox; the SVG scales to the width of the page
_L, _R, _T, _B = 52, 16, 16, 44  # margins: axis labels left, oligo names below
_FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif"


def _ticks(lo: float, hi: float) -> list[float]:
    step = 5.0 if hi - lo <= 40 else 10.0
    first = step * (lo // step + 1)
    out = []
    t = first
    while t < hi:
        out.append(t)
        t += step
    return out


def tm_chart(result: RunResult, cfg: Config) -> str | None:
    """Bar chart of oligo Tm (range bars if degenerate) against the primer PASS band and the
    annealing temperature."""
    oligos = result.oligo_qc.oligos
    if not oligos:
        return None
    names = [o.name if o.name and o.name != o.role else o.role.capitalize() for o in oligos]
    band = cfg.thresholds.primer.tm_c.pass_range
    anneal = cfg.reaction.annealing_temp_C
    top = max(max(o.tm_c_max for o in oligos), band[1]) + 6
    bottom = min(min(o.tm_c_min for o in oligos), anneal) - 8
    plot_w, plot_h = _W - _L - _R, _H - _T - _B

    def y(v: float) -> float:
        return _T + plot_h * (top - v) / (top - bottom)

    parts = [
        f'<svg class="chart" viewBox="0 0 {_W} {_H}" role="img" '
        f'aria-label="Oligo melting temperatures" font-family="{_FONT}" font-size="12">',
        # primer PASS band and its label
        f'<rect x="{_L}" y="{y(band[1]):.1f}" width="{plot_w}" '
        f'height="{y(band[0]) - y(band[1]):.1f}" fill="var(--pass-bg, #DDF0E7)"/>',
        f'<text x="{_L + 4}" y="{y(band[1]) + 13:.1f}" fill="var(--pass, #1F7A5A)" '
        f'stroke="var(--paper, #F4F6F8)" stroke-width="4" paint-order="stroke">'
        f"primer Tm, PASS band</text>",
    ]
    for t in _ticks(bottom, top):  # grid and axis labels
        parts.append(
            f'<line x1="{_L}" x2="{_W - _R}" y1="{y(t):.1f}" y2="{y(t):.1f}" '
            f'stroke="var(--rule, #D3DBE2)" stroke-width="0.6"/>'
            f'<text x="{_L - 6}" y="{y(t) + 4:.1f}" text-anchor="end" '
            f'fill="var(--muted, #55636F)">{t:g}</text>'
        )
    parts.append(
        f'<text transform="translate(14 {_T + plot_h / 2:.1f}) rotate(-90)" '
        f'text-anchor="middle" fill="var(--muted, #55636F)">Tm (°C)</text>'
    )
    slot = plot_w / len(oligos)
    bar_w = min(56.0, slot * 0.55)
    for i, (o, name) in enumerate(zip(oligos, names, strict=True)):
        cx = _L + slot * (i + 0.5)
        mid = (o.tm_c_min + o.tm_c_max) / 2
        label = escape(name)
        parts.append(
            f'<rect x="{cx - bar_w / 2:.1f}" y="{y(mid):.1f}" width="{bar_w:.1f}" '
            f'height="{y(bottom) - y(mid):.1f}" fill="#3B5B7A">'
            f"<title>{label}: {mid:.1f} °C</title></rect>"
        )
        if o.tm_c_max > o.tm_c_min:  # degenerate oligo: the range of its variants
            parts.append(
                f'<line x1="{cx:.1f}" x2="{cx:.1f}" y1="{y(o.tm_c_max):.1f}" '
                f'y2="{y(o.tm_c_min):.1f}" stroke="var(--ink, #17222D)" stroke-width="1.5"/>'
            )
            for v in (o.tm_c_min, o.tm_c_max):
                parts.append(
                    f'<line x1="{cx - 6:.1f}" x2="{cx + 6:.1f}" y1="{y(v):.1f}" '
                    f'y2="{y(v):.1f}" stroke="var(--ink, #17222D)" stroke-width="1.5"/>'
                )
        parts.append(
            f'<text x="{cx:.1f}" y="{y(o.tm_c_max) - 6:.1f}" text-anchor="middle" '
            f'fill="var(--ink, #17222D)">{mid:.1f}</text>'
            f'<text x="{cx:.1f}" y="{_H - _B + 18}" text-anchor="middle" '
            f'fill="var(--ink, #17222D)">{label}</text>'
        )
    parts.append(  # annealing temperature, drawn last so it stays visible over the bars
        f'<line x1="{_L}" x2="{_W - _R}" y1="{y(anneal):.1f}" y2="{y(anneal):.1f}" '
        f'stroke="var(--fail, #B23B3B)" stroke-width="1.5" stroke-dasharray="6 4"/>'
        f'<text x="{_W - _R - 4}" y="{y(anneal) - 6:.1f}" text-anchor="end" '
        f'fill="var(--fail, #B23B3B)" stroke="var(--paper, #F4F6F8)" stroke-width="4" '
        f'paint-order="stroke">annealing {anneal:g} °C</text>'
        f'<line x1="{_L}" x2="{_W - _R}" y1="{y(bottom):.1f}" y2="{y(bottom):.1f}" '
        f'stroke="var(--muted, #55636F)"/>'
    )
    parts.append("</svg>")
    return "".join(parts)
