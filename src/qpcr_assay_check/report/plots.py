"""Plotly figures, embedded in the report as inline HTML (no CDN)."""

from __future__ import annotations

import plotly.graph_objects as go

from ..config import Config
from ..results import RunResult

_FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
_INK = "#17222D"
_BAR = "#3B5B7A"
_BAND = "rgba(31,122,90,0.14)"
_ANNEAL = "#B23B3B"


def tm_chart(result: RunResult, cfg: Config) -> str | None:
    """Bar chart of oligo Tm (range bars if degenerate) against the annealing temperature."""
    oligos = result.oligo_qc.oligos
    roles = [o.role.capitalize() for o in oligos]
    mid = [(o.tm_c_min + o.tm_c_max) / 2 for o in oligos]
    plus = [o.tm_c_max - m for o, m in zip(oligos, mid, strict=True)]
    minus = [m - o.tm_c_min for o, m in zip(oligos, mid, strict=True)]
    band = cfg.thresholds.primer.tm_c.pass_range
    anneal = cfg.reaction.annealing_temp_C

    fig = go.Figure(
        go.Bar(
            x=roles,
            y=mid,
            error_y={"type": "data", "symmetric": False, "array": plus, "arrayminus": minus},
            marker_color=_BAR,
            text=[f"{m:.1f}" for m in mid],
            textposition="outside",
            hovertemplate="%{x}: %{y:.1f} °C<extra></extra>",
        )
    )
    fig.add_hrect(
        y0=band[0],
        y1=band[1],
        fillcolor=_BAND,
        line_width=0,
        annotation_text="primer Tm, PASS band",
        annotation_position="top left",
        annotation_font={"size": 11, "color": _INK},
        annotation_bgcolor="rgba(255,255,255,0.9)",
    )
    fig.add_hline(
        y=anneal,
        line_dash="dash",
        line_color=_ANNEAL,
        annotation_text=f"annealing {anneal:g} °C",
        annotation_position="bottom right",
        annotation_font={"size": 11, "color": _ANNEAL},
        annotation_bgcolor="rgba(255,255,255,0.9)",
    )
    top = max(max(o.tm_c_max for o in oligos), band[1]) + 6
    bottom = min(min(o.tm_c_min for o in oligos), anneal) - 8
    fig.update_layout(
        height=300,
        margin={"l": 50, "r": 20, "t": 20, "b": 40},
        yaxis={"title": "Tm (°C)", "range": [bottom, top], "gridcolor": "#E3E8ED"},
        xaxis={"showgrid": False},
        font={"family": _FONT, "size": 13, "color": _INK},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"displaylogo": False, "responsive": True},
        default_width="100%",
    )
