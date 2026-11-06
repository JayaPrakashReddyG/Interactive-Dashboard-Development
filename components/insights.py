"""Automatic business insights and downloadable analytical reports."""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from utils.calculations import (compute_kpis, concentration, customer_summary, fmt_money, fmt_num, fmt_pct,
                                group_summary, pct_change, product_trend, time_series)

_METRICS = [("Total revenue", "revenue", fmt_money), ("Total profit", "profit", fmt_money),
            ("Profit margin", "margin", fmt_pct), ("Total orders", "orders", fmt_num),
            ("Total customers", "customers", fmt_num), ("Average order value", "aov", fmt_money)]


def generate_insights(df: pd.DataFrame, prev_df: pd.DataFrame | None, start: pd.Timestamp,
                      end: pd.Timestamp) -> dict:
    """Return {'findings': [...], 'actions': [...]} computed from the selected records."""
    findings: list[dict] = []
    actions: list[dict] = []
    if df is None or df.empty:
        return {"findings": findings, "actions": actions}

    def find(kind: str, title: str, text: str) -> None:
        findings.append(dict(kind=kind, title=title, text=text))

    def act(title: str, text: str) -> None:
        actions.append(dict(kind="action", title=title, text=text))

    k = compute_kpis(df)
    pk = compute_kpis(prev_df) if prev_df is not None and not prev_df.empty else None

    if pk and pk["revenue"] > 0:
        g = pct_change(k["revenue"], pk["revenue"])
        dm = k["margin"] - pk["margin"]
        verb = "grew" if g >= 0 else "declined"
        find("positive" if g >= 0 else "negative", "Revenue growth" if g >= 0 else "Revenue decline",
             f"Revenue {verb} {abs(g):.1f}% to {fmt_money(k['revenue'])} from {fmt_money(pk['revenue'])} in the "
             f"prior period. Profit margin moved {dm:+.1f} pp to {k['margin']:.1f}%.")
        if g < 0:
            act("Diagnose the decline", "Compare category, region and product views with the prior period to see "
                "where volume was lost before changing prices or marketing spend.")
    else:
        find("neutral", "Revenue", f"Revenue is {fmt_money(k['revenue'])} from {k['orders']:,} orders at a "
             f"{k['margin']:.1f}% profit margin. No prior-period data exists to compare against.")

    cat = group_summary(df, "Category")
    top = cat.iloc[0]
    find("neutral", "Highest-revenue category", f"{top['Category']} leads with {fmt_money(top['Revenue'])}, "
         f"{top['Revenue Share %']:.1f}% of revenue.")
    if len(cat) > 1:
        by_margin = cat.sort_values("Margin %")
        lo, hi = by_margin.iloc[0], by_margin.iloc[-1]
        if hi["Margin %"] - lo["Margin %"] >= 5:
            find("neutral", "Margin spread", f"{hi['Category']} earns a {hi['Margin %']:.1f}% margin against "
                 f"{lo['Margin %']:.1f}% for {lo['Category']}.")
            act("Protect low-margin categories", f"Review discounting and supplier costs in {lo['Category']} and "
                f"shift promotion budget toward {hi['Category']}.")

    reg = group_summary(df, "Region")
    if len(reg) > 1:
        b, w = reg.iloc[0], reg.iloc[-1]
        find("positive", "Best-performing region", f"{b['Region']} leads with {fmt_money(b['Revenue'])} "
             f"({b['Revenue Share %']:.1f}% of revenue). {w['Region']} is lowest at {fmt_money(w['Revenue'])}.")
        act("Lift the weakest region", f"Replicate the {b['Region']} sales playbook in {w['Region']} and review "
            "local pricing, coverage and customer acquisition.")

    monthly = time_series(df, "Monthly")
    if len(monthly) >= 2:
        peak = monthly.loc[monthly["Revenue"].idxmax()]
        find("neutral", "Peak sales month", f"{peak['Period']:%B %Y} was the strongest month with "
             f"{fmt_money(peak['Revenue'])} in revenue.")
        act("Plan around peak demand", f"Align inventory, staffing and campaigns with the {peak['Period']:%B} peak.")

    trend = product_trend(df, start, end)
    if not trend.empty:
        dec = trend[trend["Change %"] <= -10].head(3)
        if not dec.empty:
            labels = ", ".join(f"{r['Product']} ({r['Change %']:.0f}%)" for _, r in dec.iterrows())
            find("negative", "Declining products", f"Revenue fell between the first and second half of the "
                 f"period for: {labels}.")
            act("Reposition declining products", "Test bundles, price changes or targeted promotions for "
                f"{', '.join(dec['Product'])}, or phase them out if the decline continues.")
        grow = trend[trend["Change %"] >= 10].tail(1)
        if not grow.empty:
            r = grow.iloc[0]
            find("positive", "Product momentum", f"{r['Product']} grew {r['Change %']:.0f}% between the two halves "
                 "of the period.")

    share = concentration(df)
    find("neutral", "Customer concentration", f"The top 10% of customers generate {share:.0f}% of revenue.")
    if share >= 50:
        act("Reduce concentration risk", "Broaden the customer base with acquisition campaigns and protect top "
            "accounts with dedicated account management.")
    cs = customer_summary(df, end)
    risk = cs[cs["RFM Segment"] == "At Risk"]
    if len(risk):
        act("Win back at-risk customers", f"{len(risk)} high-value customers have not purchased recently and "
            f"account for {fmt_money(risk['Revenue'].sum())} of revenue. Launch a targeted win-back offer.")
    if not actions:
        act("Maintain momentum", "Performance is balanced across categories and regions. Keep monitoring margin "
            "and customer retention each period.")
    return {"findings": findings, "actions": actions}


def _summary_table(df: pd.DataFrame, prev_df: pd.DataFrame | None) -> pd.DataFrame:
    k = compute_kpis(df)
    pk = compute_kpis(prev_df) if prev_df is not None and not prev_df.empty else None
    rows = []
    for label, key, _ in _METRICS:
        prior = pk[key] if pk else None
        change = (k[key] - prior) if (pk and key == "margin") else (pct_change(k[key], prior) if pk else None)
        rows.append({"Metric": label, "Current period": k[key], "Prior period": prior,
                     "Change": change, "Change unit": "pp" if key == "margin" else "%"})
    return pd.DataFrame(rows)


def build_text_report(df: pd.DataFrame, prev_df: pd.DataFrame | None, start: pd.Timestamp,
                      end: pd.Timestamp) -> str:
    k = compute_kpis(df)
    pk = compute_kpis(prev_df) if prev_df is not None and not prev_df.empty else None
    ins = generate_insights(df, prev_df, start, end)
    lines = ["# Business Analytics Report", "", f"Period: {start:%d %b %Y} to {end:%d %b %Y}",
             f"Records analysed: {len(df):,}", "", "## Key metrics", "",
             "| Metric | Current | Prior | Change |", "|---|---|---|---|"]
    for label, key, fmt in _METRICS:
        if pk:
            change = f"{k[key] - pk[key]:+.1f} pp" if key == "margin" else fmt_pct(pct_change(k[key], pk[key]), signed=True)
            lines.append(f"| {label} | {fmt(k[key])} | {fmt(pk[key])} | {change} |")
        else:
            lines.append(f"| {label} | {fmt(k[key])} | n/a | n/a |")
    for title, by in (("Revenue by category", "Category"), ("Revenue by region", "Region")):
        g = group_summary(df, by)
        lines += ["", f"## {title}", "", f"| {by} | Revenue | Profit | Margin |", "|---|---|---|---|"]
        lines += [f"| {r[by]} | {fmt_money(r['Revenue'])} | {fmt_money(r['Profit'])} | {fmt_pct(r['Margin %'])} |"
                  for _, r in g.iterrows()]
    g = group_summary(df, "Product").head(10)
    lines += ["", "## Top 10 products", "", "| Product | Revenue | Margin |", "|---|---|---|"]
    lines += [f"| {r['Product']} | {fmt_money(r['Revenue'])} | {fmt_pct(r['Margin %'])} |" for _, r in g.iterrows()]
    lines += ["", "## Insights", ""] + [f"- **{i['title']}**: {i['text']}" for i in ins["findings"]]
    lines += ["", "## Recommendations", ""] + [f"- **{i['title']}**: {i['text']}" for i in ins["actions"]]
    return "\n".join(lines) + "\n"


def build_excel_report(df: pd.DataFrame, prev_df: pd.DataFrame | None, start: pd.Timestamp,
                       end: pd.Timestamp) -> bytes:
    from openpyxl.styles import Font, PatternFill

    ins = generate_insights(df, prev_df, start, end)
    insight_rows = ([{"Type": "Finding", "Title": i["title"], "Detail": i["text"]} for i in ins["findings"]]
                    + [{"Type": "Recommendation", "Title": i["title"], "Detail": i["text"]} for i in ins["actions"]])
    customers = customer_summary(df, end)
    sheets = {
        "Summary": _summary_table(df, prev_df),
        "Insights": pd.DataFrame(insight_rows),
        "Monthly": time_series(df, "Monthly"),
        "Category": group_summary(df, "Category"),
        "Region": group_summary(df, "Region"),
        "State": group_summary(df, ["State", "Region"]),
        "Products": group_summary(df, ["Product", "Category"]),
        "Customers": customers,
        "Filtered Data": df.assign(**{"Order Date": df["Order Date"].dt.date}),
    }
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)
        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="0B1220")
            for col in ws.columns:
                width = max(len(str(c.value)) if c.value is not None else 0 for c in list(col)[:200])
                ws.column_dimensions[col[0].column_letter].width = min(max(width + 2, 10), 60)
    return buffer.getvalue()


@st.cache_data(show_spinner=False)
def cached_excel_report(df: pd.DataFrame, prev_df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> bytes:
    return build_excel_report(df, prev_df, start, end)


@st.cache_data(show_spinner=False)
def cached_text_report(df: pd.DataFrame, prev_df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> str:
    return build_text_report(df, prev_df, start, end)
