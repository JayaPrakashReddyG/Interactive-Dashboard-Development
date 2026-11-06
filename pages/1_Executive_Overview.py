"""Executive Overview: headline KPIs, trend, mix and automatically generated insights."""
import streamlit as st

from components import charts, kpi_cards as ui
from components.insights import generate_insights
from components.sidebar import get_context
from utils import calculations as calc

ctx = get_context()
cur, prev = ctx.current, ctx.previous
ui.page_header("Executive Overview", "Headline performance compared with the previous period of equal length.", ctx)

k = calc.compute_kpis(cur)
pk = calc.compute_kpis(prev) if not prev.empty else None
ui.render_kpis(ui.executive_kpi_items(k, pk, ctx.target_growth))

ui.section_title("Revenue and profit trend")
gran = st.radio("Granularity", list(calc.GRANULARITY), index=2, horizontal=True, key="exec_gran",
                label_visibility="collapsed")
charts.show_chart(charts.trend_chart(calc.time_series(cur, gran), f"{gran} revenue and profit", gran))

left, right = st.columns(2)
with left:
    charts.show_chart(charts.hbar(calc.group_summary(cur, "Category"), "Category", "Revenue", "Revenue by category"))
with right:
    charts.show_chart(charts.hbar(calc.group_summary(cur, "Region"), "Region", "Revenue", "Revenue by region"))

ui.section_title("Key insights and recommendations")
insights = generate_insights(cur, prev, ctx.start, ctx.end)
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**What the data shows**")
    ui.render_insights(insights["findings"])
with col_b:
    st.markdown("**Recommended actions**")
    ui.render_insights(insights["actions"])

with st.expander("Data quality report and record preview"):
    ui.render_quality(ctx.report)
    preview = cur.head(200).assign(**{"Order Date": cur["Order Date"].head(200).dt.date})
    charts._render(st.dataframe, preview, hide_index=True)
