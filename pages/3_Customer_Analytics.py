"""Customer Analytics: new vs returning, segmentation, top customers and purchase behaviour."""
import streamlit as st

from components import charts, kpi_cards as ui
from components.sidebar import get_context
from utils import calculations as calc

ctx = get_context()
cur, prev = ctx.current, ctx.previous
ui.page_header("Customer Analytics", "Who is buying, how often, and which customers drive revenue.", ctx)

cust = calc.customer_summary(cur, ctx.end)
ck = calc.customer_kpis(cur, ctx.data_all, ctx.start)
prev_n = int(prev["Customer ID"].nunique()) if not prev.empty else None
delta = calc.pct_change(ck["total"], prev_n) if prev_n else None
ui.render_kpis([
    dict(label="Unique customers", value=calc.fmt_num(ck["total"]), delta=delta, hero=True,
         prior=calc.fmt_num(prev_n) if prev_n else None),
    dict(label="New customers", value=calc.fmt_num(ck["new"]), note=f"{ck['new_share']:.0f}% of active customers"),
    dict(label="Returning customers", value=calc.fmt_num(ck["returning"]), note=f"{100 - ck['new_share']:.0f}% of active customers"),
    dict(label="Revenue per customer", value=calc.fmt_money(ck["revenue_per_customer"]), note="Average over the period"),
    dict(label="Repeat purchase rate", value=calc.fmt_pct(ck["repeat_rate"]), note="Customers with 2+ orders"),
])

ui.section_title("New versus returning customers")
charts.show_chart(charts.stacked_customers(calc.new_vs_returning(cur, ctx.data_all), "Active customers per month"))
st.caption("A customer counts as new in the month of their first recorded order in the full dataset.")

ui.section_title("Customer segmentation")
left, right = st.columns(2)
seg = calc.group_summary(cur, "Customer Segment")
rfm = (cust.groupby("RFM Segment").agg(Customers=("Customer ID", "count"), Revenue=("Revenue", "sum"))
       .reset_index().sort_values("Revenue", ascending=False))
with left:
    charts.show_chart(charts.hbar(seg, "Customer Segment", "Revenue", "Revenue by customer segment"))
with right:
    charts.show_chart(charts.hbar(rfm, "RFM Segment", "Revenue", "Revenue by value segment (recency, frequency, spend)"))
left, right = st.columns(2)
with left:
    charts.show_chart(charts.hbar(rfm.sort_values("Customers", ascending=False), "RFM Segment", "Customers",
                                  "Customers by value segment", fmt="num"))
with right:
    seg = seg.assign(**{"Avg order value": seg["Revenue"] / seg["Orders"]}).sort_values("Avg order value", ascending=False)
    charts.show_chart(charts.hbar(seg, "Customer Segment", "Avg order value", "Average order value by segment"))

ui.section_title("Top customers by spending")
left, right = st.columns([2, 3])
with left:
    charts.show_chart(charts.hbar(cust, "Customer", "Revenue", "Top 10 customers by revenue", top_n=10))
with right:
    table = cust.head(20).assign(**{"Last Order": cust.head(20)["Last Order"].dt.strftime("%d %b %Y")})
    charts.show_table(table[["Customer", "Segment", "RFM Segment", "Revenue", "Profit", "Orders", "AOV", "Last Order"]],
                      money=["Revenue", "Profit", "AOV"], height=420)

ui.section_title("Purchase behaviour")
left, right = st.columns(2)
with left:
    charts.show_chart(charts.histogram(cust["Orders"], "Customers by number of orders", "Orders per customer"))
with right:
    charts.show_chart(charts.scatter(cust, "Orders", "Revenue", "Orders versus revenue per customer", color="RFM Segment",
                                     hover="Customer", yaxis=dict(tickprefix="$", tickformat=".2s")))
