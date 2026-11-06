"""Regional Analysis: region and state performance, profit comparison and tiers."""
import streamlit as st

from components import charts, kpi_cards as ui
from components.sidebar import get_context
from utils import calculations as calc

ctx = get_context()
cur = ctx.current
ui.page_header("Regional Analysis", "Where revenue and profit come from, and which regions and states lag.", ctx)

reg = calc.group_summary(cur, "Region")
reg["Performance"] = calc.performance_tier(reg["Revenue"])
top, low = reg.iloc[0], reg.iloc[-1]
margin_best = reg.sort_values("Margin %").iloc[-1]
ui.render_kpis([
    dict(label="Active regions", value=str(len(reg)), note=f"{cur['State'].nunique()} states", hero=True),
    dict(label="Top region", value=top["Region"], note=f"{calc.fmt_money(top['Revenue'])}, {top['Revenue Share %']:.1f}% of revenue"),
    dict(label="Lowest region", value=low["Region"], note=f"{calc.fmt_money(low['Revenue'])}, {low['Revenue Share %']:.1f}% of revenue"),
    dict(label="Highest margin region", value=margin_best["Region"], note=f"{margin_best['Margin %']:.1f}% profit margin"),
])

ui.section_title("Region-wise revenue and profit")
left, right = st.columns(2)
with left:
    charts.show_chart(charts.hbar(reg, "Region", "Revenue", "Revenue by region (cyan = high, amber = low)",
                                  colors=charts.tier_colors(reg["Performance"])))
with right:
    charts.show_chart(charts.grouped_bar(reg, "Region", "Regional profit compared with revenue"))
st.caption("Tiers compare each region with the average: High is 20% or more above, Low is 20% or more below.")
charts.show_table(reg[["Region", "Performance", "Revenue", "Profit", "Margin %", "Orders", "Customers", "Revenue Share %"]],
                  money=["Revenue", "Profit"], pct=["Margin %", "Revenue Share %"], num=["Orders", "Customers"])

ui.section_title("State-wise sales performance")
states = calc.group_summary(cur, ["State", "Region"])
states["Performance"] = calc.performance_tier(states["Revenue"])
view = st.radio("Show", ["Top 10", "Bottom 10", "All states"], horizontal=True, key="state_view")
shown = states.head(10) if view == "Top 10" else states.sort_values("Revenue").head(10) if view == "Bottom 10" else states
charts.show_chart(charts.hbar(shown, "State", "Revenue", f"Revenue by state: {view.lower()}",
                              colors=charts.tier_colors(shown["Performance"])))
charts.show_table(states[["State", "Region", "Performance", "Revenue", "Profit", "Margin %", "Orders", "Revenue Share %"]],
                  money=["Revenue", "Profit"], pct=["Margin %", "Revenue Share %"], num=["Orders"], height=380)

ui.section_title("Where each region sells")
pivot = cur.pivot_table(index="Region", columns="Category", values="Revenue", aggfunc="sum", fill_value=0)
charts.show_chart(charts.heatmap(pivot, "Revenue by region and category"))
charts.show_chart(charts.multi_line(calc.series_by(cur, "Region", "Monthly"), "Period", "Revenue", "Region",
                                    "Monthly revenue by region"))
