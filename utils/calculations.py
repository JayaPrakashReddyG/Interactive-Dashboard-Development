"""Reusable business calculations and number formatting."""
from __future__ import annotations

import numpy as np
import pandas as pd

GRANULARITY = {"Daily": "D", "Weekly": "W", "Monthly": "M", "Yearly": "Y"}
_RANGE_FREQ = {"D": "D", "W": "W-MON", "M": "MS", "Y": "YS"}


# ----------------------------------------------------------------- formatting
def fmt_num(value, decimals: int = 1) -> str:
    """12_345 -> 12.3K, 2_500_000 -> 2.5M."""
    if value is None or pd.isna(value):
        return "–"
    sign = "-" if value < 0 else ""
    a = abs(float(value))
    for div, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            return f"{sign}{a / div:.{decimals}f}{suffix}"
    return f"{sign}{a:,.0f}" if a.is_integer() else f"{sign}{a:,.1f}"


def fmt_money(value, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "–"
    s = fmt_num(abs(value), decimals)
    return f"-${s}" if value < 0 else f"${s}"


def fmt_pct(value, decimals: int = 1, signed: bool = False) -> str:
    if value is None or pd.isna(value):
        return "–"
    return f"{value:+.{decimals}f}%" if signed else f"{value:.{decimals}f}%"


# ----------------------------------------------------------------------- KPIs
def compute_kpis(df: pd.DataFrame) -> dict:
    keys = ("revenue", "profit", "orders", "customers", "aov", "margin", "units")
    if df is None or df.empty:
        return {k: 0.0 for k in keys}
    revenue, profit = float(df["Revenue"].sum()), float(df["Profit"].sum())
    orders, customers = int(df["Order ID"].nunique()), int(df["Customer ID"].nunique())
    return {
        "revenue": revenue, "profit": profit, "orders": orders, "customers": customers,
        "aov": revenue / orders if orders else 0.0,
        "margin": profit / revenue * 100 if revenue else 0.0,
        "units": float(df["Quantity"].sum()),
    }


def pct_change(current, previous):
    if previous is None or pd.isna(previous) or previous == 0:
        return None
    return (current - previous) / abs(previous) * 100


def previous_period(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Rows from the period of equal length that ends the day before `start`."""
    days = (end - start).days + 1
    prev_end = start - pd.Timedelta(days=1)
    prev_start = prev_end - pd.Timedelta(days=days - 1)
    return df[(df["Order Date"] >= prev_start) & (df["Order Date"] <= prev_end)]


# ---------------------------------------------------------------- aggregation
def group_summary(df: pd.DataFrame, by) -> pd.DataFrame:
    cols = [by] if isinstance(by, str) else list(by)
    if df.empty:
        return pd.DataFrame(columns=cols + ["Revenue", "Profit", "Orders", "Quantity", "Customers",
                                            "Margin %", "Revenue Share %", "Profit Share %"])
    g = df.groupby(cols, as_index=False).agg(
        Revenue=("Revenue", "sum"), Profit=("Profit", "sum"), Orders=("Order ID", "nunique"),
        Quantity=("Quantity", "sum"), Customers=("Customer ID", "nunique"))
    g["Margin %"] = np.where(g["Revenue"] != 0, g["Profit"] / g["Revenue"] * 100, 0.0)
    g["Revenue Share %"] = g["Revenue"] / g["Revenue"].sum() * 100
    total_profit = g["Profit"].sum()
    g["Profit Share %"] = g["Profit"] / total_profit * 100 if total_profit else 0.0
    return g.sort_values("Revenue", ascending=False).reset_index(drop=True)


def _period_start(df: pd.DataFrame, granularity: str) -> pd.Series:
    return df["Order Date"].dt.to_period(GRANULARITY[granularity]).dt.start_time.rename("Period")


def time_series(df: pd.DataFrame, granularity: str = "Monthly") -> pd.DataFrame:
    cols = ["Period", "Revenue", "Profit", "Orders", "Quantity", "Margin %"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    ts = df.groupby(_period_start(df, granularity)).agg(
        Revenue=("Revenue", "sum"), Profit=("Profit", "sum"),
        Orders=("Order ID", "nunique"), Quantity=("Quantity", "sum"))
    full = pd.date_range(ts.index.min(), ts.index.max(), freq=_RANGE_FREQ[GRANULARITY[granularity]])
    ts = ts.reindex(full, fill_value=0).rename_axis("Period").reset_index()
    ts["Margin %"] = np.where(ts["Revenue"] != 0, ts["Profit"] / ts["Revenue"] * 100, 0.0)
    return ts[cols]


def series_by(df: pd.DataFrame, by: str, granularity: str = "Monthly") -> pd.DataFrame:
    period = _period_start(df, granularity)
    return df.groupby([period, df[by]]).agg(Revenue=("Revenue", "sum"), Profit=("Profit", "sum")).reset_index()


def monthly_yoy(df: pd.DataFrame) -> pd.DataFrame:
    d = df.assign(Year=df["Order Date"].dt.year, Month=df["Order Date"].dt.month)
    return d.pivot_table(index="Month", columns="Year", values="Revenue", aggfunc="sum").reindex(range(1, 13))


def performance_tier(values: pd.Series) -> np.ndarray:
    """High / Average / Low relative to the group average (+/-20%)."""
    ratio = values / values.mean() if values.mean() else values * 0
    return np.select([ratio >= 1.2, ratio <= 0.8], ["High", "Low"], default="Average")


# ------------------------------------------------------------------ customers
def _quartile(s: pd.Series, ascending: bool = True) -> pd.Series:
    if len(s) < 4:
        return pd.Series(3, index=s.index)
    ranks = s.rank(method="first", ascending=ascending)
    return pd.qcut(ranks, 4, labels=False).astype(int) + 1


def customer_summary(df: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    """One row per customer with RFM scores and an RFM segment label."""
    c = df.groupby("Customer ID").agg(
        Customer=("Customer Name", "first"), Segment=("Customer Segment", "first"),
        Revenue=("Revenue", "sum"), Profit=("Profit", "sum"), Orders=("Order ID", "nunique"),
        Units=("Quantity", "sum"), **{"First Order": ("Order Date", "min"), "Last Order": ("Order Date", "max")})
    c["AOV"] = c["Revenue"] / c["Orders"]
    c["Recency (days)"] = (as_of - c["Last Order"]).dt.days
    r = _quartile(c["Recency (days)"], ascending=False)
    f, m = _quartile(c["Orders"]), _quartile(c["Revenue"])
    c["RFM Segment"] = np.select(
        [(r >= 3) & (f >= 3) & (m >= 3), (f >= 3) & (r >= 2), (r <= 2) & (m >= 3), (r <= 2) & (f <= 2)],
        ["Champions", "Loyal", "At Risk", "Hibernating"], default="Promising")
    return c.reset_index().sort_values("Revenue", ascending=False).reset_index(drop=True)


def customer_kpis(df: pd.DataFrame, all_df: pd.DataFrame, start: pd.Timestamp) -> dict:
    first = all_df.groupby("Customer ID")["Order Date"].min()
    ids = df["Customer ID"].unique()
    total = len(ids)
    new = int((first.reindex(ids) >= start).sum())
    orders_per = df.groupby("Customer ID")["Order ID"].nunique()
    return {
        "total": total, "new": new, "returning": total - new,
        "new_share": new / total * 100 if total else 0.0,
        "revenue_per_customer": df["Revenue"].sum() / total if total else 0.0,
        "repeat_rate": float((orders_per >= 2).mean() * 100) if total else 0.0,
    }


def new_vs_returning(df: pd.DataFrame, all_df: pd.DataFrame) -> pd.DataFrame:
    """Monthly active customers split by whether it is their first-ever purchase month."""
    first = all_df.groupby("Customer ID")["Order Date"].min()
    d = df[["Order Date", "Customer ID"]].copy()
    d["Period"] = d["Order Date"].dt.to_period("M").dt.start_time
    d["First"] = d["Customer ID"].map(first).dt.to_period("M").dt.start_time
    d["Type"] = np.where(d["First"] == d["Period"], "New", "Returning")
    out = (d.drop_duplicates(["Period", "Customer ID"]).groupby(["Period", "Type"]).size()
           .unstack(fill_value=0).reindex(columns=["New", "Returning"], fill_value=0).reset_index())
    return out


def concentration(df: pd.DataFrame, top_share: float = 0.10) -> float:
    """Share of revenue (%) earned by the top `top_share` of customers."""
    r = df.groupby("Customer ID")["Revenue"].sum().sort_values(ascending=False)
    if r.empty or r.sum() == 0:
        return 0.0
    k = max(1, int(np.ceil(len(r) * top_share)))
    return float(r.head(k).sum() / r.sum() * 100)


# ------------------------------------------------------------------- products
def product_trend(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Revenue change per product between the first and second half of the period."""
    cols = ["Product", "First Half", "Second Half", "Change %"]
    span = (end - start).days
    if span < 13 or df.empty:
        return pd.DataFrame(columns=cols)
    mid = start + pd.Timedelta(days=span // 2)
    a = df[df["Order Date"] <= mid].groupby("Product")["Revenue"].sum().rename("First Half")
    b = df[df["Order Date"] > mid].groupby("Product")["Revenue"].sum().rename("Second Half")
    t = pd.concat([a, b], axis=1).fillna(0)
    t = t[t["First Half"] > 0].copy()
    t["Change %"] = (t["Second Half"] - t["First Half"]) / t["First Half"] * 100
    return t.reset_index().rename(columns={"index": "Product"}).sort_values("Change %").reset_index(drop=True)[cols]
