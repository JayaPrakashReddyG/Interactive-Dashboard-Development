"""Interactive Business Analytics Dashboard - application entry point.

Run with:  python -m streamlit run app.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Business Analytics Dashboard", layout="wide", initial_sidebar_state="expanded")

from components.sidebar import build_context  # noqa: E402

navigation = st.navigation([
    st.Page("pages/1_Executive_Overview.py", title="Executive Overview", url_path="executive-overview", default=True),
    st.Page("pages/2_Sales_Analysis.py", title="Sales Analysis", url_path="sales-analysis"),
    st.Page("pages/3_Customer_Analytics.py", title="Customer Analytics", url_path="customer-analytics"),
    st.Page("pages/4_Product_Performance.py", title="Product Performance", url_path="product-performance"),
    st.Page("pages/5_Regional_Analysis.py", title="Regional Analysis", url_path="regional-analysis"),
])

ctx = build_context()
if ctx.current.empty:
    st.warning("No records match the current filters. Widen the date range or select more regions, "
               "categories or segments in the sidebar, or press Reset filters.")
    st.stop()

navigation.run()
