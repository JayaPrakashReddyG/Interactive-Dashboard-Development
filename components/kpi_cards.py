"""Page header, KPI cards and text blocks (HTML rendered through Streamlit markdown)."""
from __future__ import annotations

import html

import streamlit as st

from utils import calculations as calc


def page_header(title: str, subtitle: str, ctx) -> None:
    st.markdown(
        f"<div class='page-title'>{html.escape(title)}</div>"
        f"<div class='page-sub'>{html.escape(subtitle)}</div>"
        f"<div class='page-meta'>{ctx.start:%d %b %Y} to {ctx.end:%d %b %Y} &nbsp;|&nbsp; "
        f"{len(ctx.current):,} records &nbsp;|&nbsp; {html.escape(ctx.source)}</div>",
        unsafe_allow_html=True)


def section_title(text: str) -> None:
    st.markdown(f"<div class='section-title'>{html.escape(text)}</div>", unsafe_allow_html=True)


def kpi_card(label: str, value: str, delta: float | None = None, unit: str = "%", prior: str | None = None,
             note: str | None = None, footer: dict | None = None, hero: bool = False, tone: str = "") -> str:
    esc = html.escape
    if note is not None:
        sub = f"<span class='kpi-prior'>{esc(note)}</span>"
    elif delta is None:
        sub = "<span class='kpi-prior'>No prior-period data</span>"
    else:
        cls, arrow = ("pos", "▲") if delta >= 0 else ("neg", "▼")
        sub = f"<span class='kpi-delta {cls}'>{arrow} {abs(delta):.1f}{unit}</span>"
        if prior:
            sub += f"<span class='kpi-prior'> vs {esc(prior)} prior</span>"
    foot = ""
    if footer:
        att = footer["attained"]
        cls = "pos" if att >= 100 else "neg"
        foot = (f"<div class='kpi-bar {cls}'><span style='width:{min(max(att, 0), 100):.0f}%'></span></div>"
                f"<div class='kpi-foot {cls}'>{esc(footer['text'])}</div>")
    size = " text" if len(str(value)) > 14 else ""
    return (f"<div class='kpi{' hero' if hero else ''}'><div class='kpi-label'>{esc(label)}</div>"
            f"<div class='kpi-value{size} {tone}'>{esc(str(value))}</div><div>{sub}</div>{foot}</div>")


def render_kpis(items: list[dict]) -> None:
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        col.markdown(kpi_card(**item), unsafe_allow_html=True)


def kpi_item(label: str, key: str, k: dict, pk: dict | None, fmt, mode: str = "pct",
             hero: bool = False, footer: dict | None = None) -> dict:
    """Build a KPI card definition with a previous-period comparison."""
    cur = k[key]
    if pk is None:
        delta, unit, prior = None, "%", None
    elif mode == "pp":
        delta, unit, prior = cur - pk[key], " pp", fmt(pk[key])
    else:
        delta, unit, prior = calc.pct_change(cur, pk[key]), "%", fmt(pk[key])
    return dict(label=label, value=fmt(cur), delta=delta, unit=unit, prior=prior, hero=hero, footer=footer)


def executive_kpi_items(k: dict, pk: dict | None, target_growth: float) -> list[dict]:
    footer = None
    if pk and pk["revenue"] > 0:
        required = pk["revenue"] * (1 + target_growth / 100)
        attained = k["revenue"] / required * 100 if required else 0
        footer = dict(text=f"Target {target_growth:+.0f}% growth: {attained:.0f}% attained", attained=attained)
    growth = calc.pct_change(k["revenue"], pk["revenue"]) if pk else None
    return [
        kpi_item("Total revenue", "revenue", k, pk, calc.fmt_money, hero=True, footer=footer),
        kpi_item("Profit margin", "margin", k, pk, calc.fmt_pct, mode="pp"),
        dict(label="Revenue growth", value=calc.fmt_pct(growth, signed=True) if growth is not None else "–",
             note=f"vs {calc.fmt_money(pk['revenue'])} prior" if pk else "No prior-period data",
             tone="" if growth is None else ("pos" if growth >= 0 else "neg")),
        kpi_item("Total orders", "orders", k, pk, calc.fmt_num),
        kpi_item("Total customers", "customers", k, pk, calc.fmt_num),
        kpi_item("Average order value", "aov", k, pk, calc.fmt_money),
    ]


def render_insights(items: list[dict]) -> None:
    if not items:
        st.caption("Not enough data in the current selection to generate insights.")
    for it in items:
        st.markdown(
            f"<div class='insight {it['kind']}'><b>{html.escape(it['title'])}</b>"
            f"<p>{html.escape(it['text'])}</p></div>", unsafe_allow_html=True)


def render_quality(report: dict) -> None:
    cols = st.columns(5)
    metrics = [("Raw rows", report["rows_raw"]), ("Clean rows", report["rows_clean"]),
               ("Duplicates removed", report["duplicates_removed"]),
               ("Invalid dates removed", report["invalid_dates_removed"]),
               ("Invalid rows removed", report["invalid_rows_removed"])]
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, f"{value:,}")
    if report["values_imputed"]:
        st.caption("Missing values filled: " + ", ".join(f"{k} ({v:,})" for k, v in report["values_imputed"].items()))
    if report["columns_defaulted"]:
        st.caption("Columns not in the file, defaults applied: " + "; ".join(report["columns_defaulted"]))
    if not (report["values_imputed"] or report["columns_defaulted"] or report["duplicates_removed"]
            or report["invalid_dates_removed"] or report["invalid_rows_removed"]):
        st.caption("Validation passed with no corrections needed.")
