"""Product Performance: best and worst sellers, categories, quantities and profit contribution."""
import streamlit as st

from components import charts, kpi_cards as ui
from components.sidebar import get_context
from utils import calculations as calc

ctx = get_context()
cur, prev = ctx.current, ctx.previous
ui.page_header("Product Performance", "Which products and categories earn revenue and profit, and which are fading.", ctx)

prod = calc.group_summary(cur, ["Product", "Category"])
k = calc.compute_kpis(cur)
pk = calc.compute_kpis(prev) if not prev.empty else None
best, worst = prod.iloc[0], prod.iloc[-1]
prev_products = int(prev["Product"].nunique()) if not prev.empty else None
ui.render_kpis([
    dict(label="Active products", value=str(len(prod)), delta=calc.pct_change(len(prod), prev_products) if prev_products else None,
         prior=str(prev_products) if prev_products else None, hero=True),
    ui.kpi_item("Units sold", "units", k, pk, calc.fmt_num),
    dict(label="Best seller", value=best["Product"], note=f"{calc.fmt_money(best['Revenue'])}, {best['Revenue Share %']:.1f}% of revenue"),
    dict(label="Lowest performer", value=worst["Product"], note=f"{calc.fmt_money(worst['Revenue'])}, {worst['Revenue Share %']:.1f}% of revenue"),
])

ui.section_title("Best-selling and lowest-performing products")
left, right = st.columns(2)
with left:
    charts.show_chart(charts.hbar(prod, "Product", "Revenue", "Top 10 products by revenue", top_n=10))
with right:
    charts.show_chart(charts.hbar(prod.sort_values("Revenue"), "Product", "Revenue", "Bottom 10 products by revenue",
                                  top_n=10, color=charts.AMBER))

ui.section_title("Category and quantity analysis")
cat = calc.group_summary(cur, "Category")
left, right = st.columns(2)
with left:
    charts.show_chart(charts.hbar(cat, "Category", "Revenue", "Category-wise revenue"))
with right:
    charts.show_chart(charts.hbar(prod.sort_values("Quantity", ascending=False), "Product", "Quantity",
                                  "Top 10 products by units sold", fmt="num", top_n=10, color=charts.BLUE))

ui.section_title("Profit contribution")
left, right = st.columns(2)
with left:
    charts.show_chart(charts.hbar(cat.sort_values("Profit Share %", ascending=False), "Category", "Profit Share %",
                                  "Share of total profit by category", fmt="pct"))
with right:
    charts.show_chart(charts.hbar(prod.sort_values("Profit Share %", ascending=False), "Product", "Profit Share %",
                                  "Share of total profit, top 10 products", fmt="pct", top_n=10))
charts.show_chart(charts.scatter(prod, "Revenue", "Margin %", "Revenue versus margin by product (bubble size = units sold)",
                                 color="Category", size="Quantity", hover="Product",
                                 xaxis=dict(tickprefix="$", tickformat=".2s"), yaxis=dict(ticksuffix="%")))

ui.section_title("Products with changing performance")
st.caption("Compares revenue in the first and second half of the selected date range.")
trend = calc.product_trend(cur, ctx.start, ctx.end)
if trend.empty:
    st.info("Select a date range of at least two weeks to see product trends.")
else:
    left, right = st.columns(2)
    declining = trend[trend["Change %"] < 0].head(10)
    growing = trend[trend["Change %"] > 0].sort_values("Change %", ascending=False).head(10)
    with left:
        st.markdown("**Declining products**")
        charts.show_table(declining, money=["First Half", "Second Half"], pct=["Change %"]) if len(declining) else st.caption("No declining products.")
    with right:
        st.markdown("**Growing products**")
        charts.show_table(growing, money=["First Half", "Second Half"], pct=["Change %"]) if len(growing) else st.caption("No growing products.")

ui.section_title("Product table")
query = st.text_input("Search products", key="prod_search", placeholder="Type part of a product or category name")
table = prod[prod["Product"].str.contains(query, case=False, regex=False) | prod["Category"].str.contains(query, case=False, regex=False)] if query else prod
charts.show_table(table[["Product", "Category", "Revenue", "Profit", "Margin %", "Quantity", "Orders", "Revenue Share %"]],
                  money=["Revenue", "Profit"], pct=["Margin %", "Revenue Share %"], num=["Quantity", "Orders"], height=420)

with st.expander("Optional statistical analysis: correlation of price, quantity, revenue and profit"):
    st.pyplot(charts.correlation_figure(cur), clear_figure=True)
