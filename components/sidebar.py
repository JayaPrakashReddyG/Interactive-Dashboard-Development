"""Sidebar: data source, interactive filters, targets, exports and the shared page context."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from components.insights import cached_excel_report, cached_text_report
from utils.calculations import previous_period
from utils.data_loader import load_sample_data, load_uploaded_data

CSS_PATH = Path(__file__).resolve().parents[1] / "assets" / "style.css"
FILTER_KEYS = ("f_region", "f_category", "f_segment")


@dataclass
class DashboardContext:
    data_all: pd.DataFrame      # every cleaned record
    scoped: pd.DataFrame        # region / category / segment filters applied, all dates
    current: pd.DataFrame       # all filters applied (selected date range)
    previous: pd.DataFrame      # same filters, previous period of equal length
    start: pd.Timestamp
    end: pd.Timestamp
    report: dict
    source: str
    target_growth: float


def get_context() -> DashboardContext:
    return st.session_state["ctx"]


def _inject_css() -> None:
    try:
        st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    except OSError:
        pass


def _section(text: str) -> None:
    st.markdown(f"<div class='side-title'>{text}</div>", unsafe_allow_html=True)


def _data_source() -> tuple[pd.DataFrame, dict, str]:
    _section("Data source")
    choice = st.radio("Dataset", ["Built-in sample", "Upload CSV / Excel"], key="data_source",
                      label_visibility="collapsed")
    if choice.startswith("Upload"):
        uploaded = st.file_uploader("CSV or Excel file", type=["csv", "xlsx", "xlsm"], key="uploaded_file")
        st.caption("Required: Order Date, Product, Revenue (or Quantity + Unit Price), Cost or Profit. "
                   "Optional: Order ID, Customer ID / Name, Category, Region, State, Customer Segment.")
        if uploaded is not None:
            try:
                df, report = load_uploaded_data(uploaded.name, uploaded.getvalue())
                return df, report, f"Uploaded file: {uploaded.name}"
            except Exception as exc:  # noqa: BLE001 - show any parsing problem to the user
                st.error(f"This file could not be used. {exc}")
                st.caption("Showing the built-in sample dataset instead.")
        else:
            st.info("Upload a file to analyse your own data. The sample dataset is shown meanwhile.")
    df, report = load_sample_data()
    return df, report, "Built-in sample dataset"


def _reset_filters() -> None:
    for key, value in st.session_state["_defaults"].items():
        st.session_state[key] = value


def _sync_filter_state(df: pd.DataFrame, source: str) -> tuple[date, date]:
    dmin, dmax = df["Order Date"].min().date(), df["Order Date"].max().date()
    defaults = {"f_dates": (dmin, dmax), "f_region": sorted(df["Region"].unique()),
                "f_category": sorted(df["Category"].unique()), "f_segment": sorted(df["Customer Segment"].unique())}
    st.session_state["_defaults"] = defaults
    signature = (source, len(df), dmin, dmax)
    if st.session_state.get("_signature") != signature:   # new dataset: start from a clean filter state
        st.session_state["_signature"] = signature
        for key, value in defaults.items():
            st.session_state[key] = value
    return dmin, dmax


def build_context() -> DashboardContext:
    """Render the sidebar, apply every filter and store the result for the pages."""
    _inject_css()
    with st.sidebar:
        df, report, source = _data_source()
        dmin, dmax = _sync_filter_state(df, source)

        _section("Filters")
        st.date_input("Date range", min_value=dmin, max_value=dmax, key="f_dates")
        st.multiselect("Region", st.session_state["_defaults"]["f_region"], key="f_region")
        st.multiselect("Product category", st.session_state["_defaults"]["f_category"], key="f_category")
        st.multiselect("Customer segment", st.session_state["_defaults"]["f_segment"], key="f_segment")
        st.button("Reset filters", on_click=_reset_filters, key="reset_filters")

        selected = st.session_state["f_dates"]
        if isinstance(selected, (list, tuple)) and len(selected) == 2:
            start_d, end_d = selected
        else:
            start_d, end_d = dmin, dmax
            st.caption("Pick an end date to apply the date range.")

        _section("Targets")
        target = st.number_input("Revenue growth target vs prior period (%)", min_value=-50.0, max_value=200.0,
                                 value=10.0, step=1.0, key="target_growth")

        start, end = pd.Timestamp(start_d), pd.Timestamp(end_d)
        scoped = df[df["Region"].isin(st.session_state["f_region"])
                    & df["Category"].isin(st.session_state["f_category"])
                    & df["Customer Segment"].isin(st.session_state["f_segment"])]
        current = scoped[(scoped["Order Date"] >= start) & (scoped["Order Date"] <= end)]
        previous = previous_period(scoped, start, end)

        if not current.empty:
            _section("Export")
            st.download_button("Filtered data (CSV)", current.to_csv(index=False).encode("utf-8"),
                               "filtered_sales_data.csv", "text/csv", key="dl_csv")
            st.download_button("Analytical report (Excel)", cached_excel_report(current, previous, start, end),
                               "business_analytics_report.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_xlsx")
            st.download_button("Summary report (Markdown)",
                               cached_text_report(current, previous, start, end).encode("utf-8"),
                               "business_analytics_summary.md", "text/markdown", key="dl_md")
        st.caption(f"{source} | {len(df):,} records loaded")

    ctx = DashboardContext(df, scoped, current, previous, start, end, report, source, float(target))
    st.session_state["ctx"] = ctx
    return ctx
