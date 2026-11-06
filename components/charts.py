"""Plotly / matplotlib chart builders with a shared dark BI theme."""
from __future__ import annotations

import calendar
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.calculations import fmt_money, fmt_num, fmt_pct

CYAN, BLUE, AMBER, SLATE = "#22D3EE", "#3B82F6", "#F59E0B", "#64748B"
PALETTE = [CYAN, BLUE, "#6366F1", "#14B8A6", "#94A3B8", AMBER, "#A78BFA", "#38BDF8"]
TIER_COLORS = {"High": CYAN, "Average": "#4B6A9B", "Low": AMBER}
PLOT_CONFIG = {"displayModeBar": False, "responsive": True}
_DATE_FMT = {"Daily": "%d %b %y", "Weekly": "%d %b %y", "Monthly": "%b %Y", "Yearly": "%Y"}


# ------------------------------------------------------------ streamlit glue
def _is_new_streamlit() -> bool:
    parts = [int(p) for p in re.findall(r"\d+", st.__version__)[:2]]
    return tuple(parts) >= (1, 50)


def _render(fn, *args, **kwargs):
    """Call a Streamlit element so it fills the container on old and new versions."""
    if _is_new_streamlit():
        try:
            return fn(*args, width="stretch", **kwargs)
        except Exception:  # noqa: BLE001 - fall back to the legacy argument
            pass
    return fn(*args, use_container_width=True, **kwargs)


def show_chart(fig: go.Figure) -> None:
    _render(st.plotly_chart, fig, config=PLOT_CONFIG)


def show_table(df: pd.DataFrame, money=(), pct=(), num=(), height: int | None = None) -> None:
    """Display a table with K / M / % formatting applied to the named columns."""
    d = df.copy()
    for col in money:
        d[col] = d[col].map(fmt_money)
    for col in pct:
        d[col] = d[col].map(fmt_pct)
    for col in num:
        d[col] = d[col].map(fmt_num)
    kwargs = {"hide_index": True}
    if height:
        kwargs["height"] = height
    _render(st.dataframe, d, **kwargs)


# ---------------------------------------------------------------------- style
def _fmt(value, kind: str) -> str:
    return {"money": fmt_money, "pct": fmt_pct, "num": fmt_num}[kind](value)


def _style(fig: go.Figure, title: str, height: int = 360, legend: bool = False) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15, color="#E5ECF6")),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Helvetica, Arial, sans-serif", color="#B6C2D9", size=12),
        margin=dict(l=8, r=8, t=56, b=8), height=height, showlegend=legend,
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right", title_text=""),
        hoverlabel=dict(bgcolor="#111A2E", font_color="#E5ECF6", bordercolor="#1E2A44"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#1E2A44")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148,163,184,0.10)", zeroline=False)
    return fig


def threshold_colors(values, reference: float) -> list[str]:
    return [CYAN if v >= reference else AMBER for v in values]


def tier_colors(tiers) -> list[str]:
    return [TIER_COLORS.get(t, SLATE) for t in tiers]


# --------------------------------------------------------------------- charts
def trend_chart(ts: pd.DataFrame, title: str, granularity: str = "Monthly") -> go.Figure:
    fig = go.Figure()
    mode = "lines+markers" if len(ts) <= 36 else "lines"
    hover_x = _DATE_FMT[granularity]
    if granularity == "Daily":
        fig.add_trace(go.Scatter(x=ts["Period"], y=ts["Revenue"], name="Daily revenue", mode="lines",
                                 line=dict(color="#35506B", width=1),
                                 hovertemplate=f"%{{x|{hover_x}}}<br>Revenue: $%{{y:,.0f}}<extra></extra>"))
        fig.add_trace(go.Scatter(x=ts["Period"], y=ts["Revenue"].rolling(7, min_periods=1).mean(),
                                 name="Revenue (7-day average)", mode="lines", line=dict(color=CYAN, width=2.5),
                                 hovertemplate=f"%{{x|{hover_x}}}<br>7-day avg: $%{{y:,.0f}}<extra></extra>"))
    else:
        fig.add_trace(go.Scatter(x=ts["Period"], y=ts["Revenue"], name="Revenue", mode=mode,
                                 line=dict(color=CYAN, width=2.5), marker=dict(size=6),
                                 hovertemplate=f"%{{x|{hover_x}}}<br>Revenue: $%{{y:,.0f}}<extra></extra>"))
    fig.add_trace(go.Scatter(x=ts["Period"], y=ts["Profit"], name="Profit", mode=mode,
                             line=dict(color=BLUE, width=2), marker=dict(size=5),
                             hovertemplate=f"%{{x|{hover_x}}}<br>Profit: $%{{y:,.0f}}<extra></extra>"))
    fig.add_hline(y=float(ts["Revenue"].mean()), line_dash="dot", line_color=SLATE,
                  annotation_text="Average revenue", annotation_position="top left",
                  annotation_font_color="#8FA1BE")
    _style(fig, title, legend=True)
    fig.update_xaxes(tickformat=_DATE_FMT[granularity])
    fig.update_yaxes(tickprefix="$", tickformat=".2s")
    return fig


def hbar(df: pd.DataFrame, cat: str, val: str, title: str, fmt: str = "money",
         top_n: int | None = None, color: str = CYAN, colors=None, height: int | None = None) -> go.Figure:
    """Horizontal bar chart plotted in the order given (first row on top)."""
    d = df.head(top_n) if top_n else df
    labels = [_fmt(v, fmt) for v in d[val]]
    fig = go.Figure(go.Bar(
        x=d[val], y=d[cat], orientation="h", marker_color=list(colors) if colors is not None else color,
        text=labels, textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>%{text}<extra></extra>"))
    _style(fig, title, height=height or max(250, 32 * len(d) + 90))
    fig.update_yaxes(autorange="reversed", showgrid=False, automargin=True)
    fig.update_xaxes(visible=False, showgrid=False)
    return fig


def grouped_bar(df: pd.DataFrame, cat: str, title: str) -> go.Figure:
    fig = go.Figure()
    for col, color in (("Revenue", CYAN), ("Profit", BLUE)):
        fig.add_trace(go.Bar(x=df[cat], y=df[col], name=col, marker_color=color,
                             text=[fmt_money(v) for v in df[col]], textposition="outside", cliponaxis=False,
                             hovertemplate=f"%{{x}}<br>{col}: %{{text}}<extra></extra>"))
    _style(fig, title, legend=True)
    fig.update_layout(barmode="group", bargap=0.25)
    fig.update_yaxes(visible=False, showgrid=False)
    return fig


def yoy_chart(pivot: pd.DataFrame, title: str) -> go.Figure:
    years = [c for c in pivot.columns]
    shades = ["#475569", "#6366F1", BLUE, CYAN]
    fig = go.Figure()
    for i, year in enumerate(years):
        recent = i == len(years) - 1
        color = shades[-(len(years) - i)] if len(years) <= len(shades) else PALETTE[i % len(PALETTE)]
        fig.add_trace(go.Scatter(
            x=[calendar.month_abbr[m] for m in pivot.index], y=pivot[year], name=str(year), mode="lines+markers",
            line=dict(color=color, width=3 if recent else 2), marker=dict(size=5),
            hovertemplate=f"%{{x}} {year}<br>Revenue: $%{{y:,.0f}}<extra></extra>"))
    _style(fig, title, legend=True)
    fig.update_yaxes(tickprefix="$", tickformat=".2s")
    return fig


def stacked_customers(nr: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    for col, color in (("Returning", BLUE), ("New", CYAN)):
        fig.add_trace(go.Bar(x=nr["Period"], y=nr[col], name=col, marker_color=color,
                             hovertemplate=f"%{{x|%b %Y}}<br>{col}: %{{y:,}}<extra></extra>"))
    _style(fig, title, legend=True)
    fig.update_layout(barmode="stack", bargap=0.25)
    fig.update_xaxes(tickformat="%b %Y")
    return fig


def histogram(series: pd.Series, title: str, xtitle: str) -> go.Figure:
    top = int(series.max()) if len(series) else 1
    xbins = dict(start=0.5, end=top + 0.5, size=1) if top <= 40 else None
    fig = go.Figure(go.Histogram(x=series, marker_color=CYAN, xbins=xbins, nbinsx=30,
                                 hovertemplate="%{x} orders<br>%{y} customers<extra></extra>"))
    _style(fig, title)
    fig.update_layout(bargap=0.08)
    fig.update_xaxes(title=xtitle)
    fig.update_yaxes(title="Customers")
    return fig


def scatter(df: pd.DataFrame, x: str, y: str, title: str, color: str | None = None, size: str | None = None,
            hover: str | None = None, xaxis: dict | None = None, yaxis: dict | None = None) -> go.Figure:
    fig = px.scatter(df, x=x, y=y, color=color, size=size, hover_name=hover, size_max=26,
                     color_discrete_sequence=PALETTE, opacity=0.85)
    _style(fig, title, height=420, legend=color is not None)
    fig.update_xaxes(**(xaxis or {}))
    fig.update_yaxes(**(yaxis or {}))
    return fig


def heatmap(pivot: pd.DataFrame, title: str) -> go.Figure:
    text = [[fmt_money(v) for v in row] for row in pivot.values]
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=list(pivot.columns), y=list(pivot.index), text=text, texttemplate="%{text}",
        colorscale=[[0, "#0F1A2E"], [1, CYAN]], showscale=False, xgap=3, ygap=3,
        hovertemplate="%{y} · %{x}<br>Revenue: %{text}<extra></extra>"))
    _style(fig, title, height=max(260, 50 * len(pivot) + 110))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return fig


def multi_line(df: pd.DataFrame, x: str, y: str, color: str, title: str) -> go.Figure:
    fig = px.line(df, x=x, y=y, color=color, color_discrete_sequence=PALETTE)
    fig.update_traces(line_width=2, hovertemplate="%{x|%b %Y}<br>%{fullData.name}: $%{y:,.0f}<extra></extra>")
    _style(fig, title, legend=True)
    fig.update_xaxes(tickformat="%b %Y", title="")
    fig.update_yaxes(tickprefix="$", tickformat=".2s", title="")
    return fig


def correlation_figure(df: pd.DataFrame):
    """Optional statistical view: correlation of numeric drivers (seaborn + matplotlib)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    d = df[["Quantity", "Unit Price", "Revenue", "Cost", "Profit"]].astype(float).copy()
    d["Margin %"] = np.where(d["Revenue"] != 0, d["Profit"] / d["Revenue"] * 100, 0.0)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    fig.patch.set_facecolor("#0B1220")
    ax.set_facecolor("#0B1220")
    sns.heatmap(d.corr(), annot=True, fmt=".2f", cmap="mako", vmin=-1, vmax=1, linewidths=1,
                linecolor="#0B1220", ax=ax, annot_kws={"color": "#E5ECF6", "size": 9})
    ax.tick_params(colors="#B6C2D9")
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(colors="#B6C2D9")
    fig.tight_layout()
    return fig
