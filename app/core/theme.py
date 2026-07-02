"""Shared visual theme (dataviz reference palette, light mode).

Categorical slots keep a FIXED order (CVD-safe ordering from the validated
reference palette); status colors are reserved for maintenance states and are
never used as series colors.
"""
import plotly.graph_objects as go

# Categorical (fixed order, never cycled)
CAT = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]
BLUE, AQUA, YELLOW, GREEN, VIOLET, RED, MAGENTA, ORANGE = CAT

# Sequential blue ramp (magnitude)
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

# Status (reserved: maintenance flags; always paired with icon/label)
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

# Fixed species -> color mapping (color follows the entity across all pages)
SPECIES_COLOR = {
    "CO₂": BLUE, "H₂O": AQUA, "NOₓ": ORANGE, "CO": YELLOW,
    "HC": MAGENTA, "SOₓ": VIOLET, "soot": INK_2, "contrails": RED,
}


def layout(fig: go.Figure, title: str | None = None, height: int = 380) -> go.Figure:
    """Apply the shared chart chrome: recessive grid/axes, muted ink, no clutter."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=INK)) if title else None,
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family='system-ui, "Segoe UI", sans-serif', color=INK_2, size=12),
        height=height, margin=dict(l=10, r=10, t=48 if title else 16, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(color=INK_2)),
        hoverlabel=dict(bgcolor="#ffffff", font=dict(color=INK)),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=BASELINE, tickfont=dict(color=MUTED),
                     title_font=dict(color=MUTED), zeroline=False)
    fig.update_yaxes(gridcolor=GRID, linecolor=BASELINE, tickfont=dict(color=MUTED),
                     title_font=dict(color=MUTED), zeroline=False)
    return fig
