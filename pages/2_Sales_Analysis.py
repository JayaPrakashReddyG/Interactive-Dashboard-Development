"""Sales Performance Analysis: trends, mix, top products and sales versus profit."""
import streamlit as st

from components import charts, kpi_cards as ui
from components.sidebar import get_context
from utils import calculations as calc

ctx = get_context()
cur, prev = ctx.current, ctx.previous
ui.page_header("Sales Performance Analysis",
               "Revenue trends, category and region mix, product leaders and sales versus profit.", ctx)

k = calc.compute_kpis(cur)
pk = calc.compute_kpis(prev) if not prev.empty else None
ui.render_kpis([
    ui.kpi_item("Total revenue", "revenue", k, pk, calc.fmt_money, hero=True),
    ui.kpi_item("Total profit", "profit", k, pk, calc.fmt_money),
    ui.kpi_item("Profit margin", "margin", k, pk, calc.fmt_pct, mode="pp"),
    ui.kpi_item("Units sold", "units", k, pk, calc.fmt_num),
])

ui.section_title("Revenue over time")
tabs = st.tabs(list(calc.GRANULARITY))
for tab, gran in zip(tabs, calc.GRANULARITY):
    with tab:
        charts.show_chart(charts.trend_chart(calc.time_series(cur, gran), f"{gran} revenue and profit", gran))

yoy = calc.monthly_yoy(cur).dropna(axis=1, how="all")
if yoy.shape[1] >= 2:
    charts.show_chart(charts.yoy_chart(yoy, "Monthly revenue compared across years"))

ui.section_title("Revenue mix")
left, right = st.columns(2)
with left:
    charts.show_chart(charts.hbar(calc.group_summary(cur, "Category"), "Category", "Revenue", "Revenue by product category"))
with right:
    charts.show_chart(charts.hbar(calc.group_summary(cur, "Region"), "Region", "Revenue", "Revenue by region"))
charts.show_chart(charts.hbar(calc.group_summary(cur, "Product"), "Product", "Revenue", "Top 10 products by revenue", top_n=10))

ui.section_title("Sales versus profit")
dim = st.selectbox("Compare by", ["Category", "Region", "Customer Segment", "State"], key="sales_dim")
g = calc.group_summary(cur, dim).head(12)
left, right = st.columns(2)
with left:
    charts.show_chart(charts.grouped_bar(g, dim, f"Revenue and profit by {dim.lower()}"))
with right:
    by_margin = g.sort_values("Margin %", ascending=False)
    colors = charts.threshold_colors(by_margin["Margin %"], k["margin"])
    charts.show_chart(charts.hbar(by_margin, dim, "Margin %", f"Profit margin by {dim.lower()} (cyan = above average)",
                                  fmt="pct", colors=colors))

ui.section_title("Monthly summary")
m = calc.time_series(cur, "Monthly")
m["MoM Revenue %"] = m["Revenue"].pct_change() * 100
m["Period"] = m["Period"].dt.strftime("%b %Y")
charts.show_table(m.iloc[::-1][["Period", "Revenue", "Profit", "Margin %", "Orders", "Quantity", "MoM Revenue %"]],
                  money=["Revenue", "Profit"], pct=["Margin %", "MoM Revenue %"], num=["Orders", "Quantity"])
