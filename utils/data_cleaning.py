"""Dataset validation and cleaning.

Accepts uploads with flexible column names, fixes data types, removes duplicates,
fills or drops missing values and returns a cleaned DataFrame plus a quality report.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd


class DataValidationError(ValueError):
    """Raised when a dataset cannot be turned into a usable sales table."""


CANONICAL_COLUMNS = [
    "Order ID", "Order Date", "Customer ID", "Customer Name", "Product", "Category",
    "Region", "State", "Quantity", "Unit Price", "Revenue", "Cost", "Profit",
    "Customer Segment",
]

ALIASES = {
    "Order ID": ["orderid", "order no", "order number", "invoice", "invoice no", "transaction id"],
    "Order Date": ["date", "orderdate", "purchase date", "transaction date", "invoice date"],
    "Customer ID": ["customerid", "cust id", "customer no", "client id"],
    "Customer Name": ["customer", "client", "client name", "cust name"],
    "Product": ["product name", "item", "item name", "sku name"],
    "Category": ["product category", "item category", "department"],
    "Region": ["sales region", "zone", "territory"],
    "State": ["province", "state province", "state name"],
    "Quantity": ["qty", "units", "units sold", "quantity sold"],
    "Unit Price": ["price", "unitprice", "selling price", "price per unit"],
    "Revenue": ["sales", "total sales", "amount", "total", "sales amount", "total revenue", "net sales"],
    "Cost": ["total cost", "cogs", "cost of goods sold"],
    "Profit": ["net profit", "gross profit"],
    "Customer Segment": ["segment", "customer type", "customer group"],
}


def _norm(name: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(name).lower()).strip()


_LOOKUP = {_norm(alias): canon for canon, aliases in ALIASES.items() for alias in [canon, *aliases]}


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename recognised columns to the canonical names used across the app."""
    mapping, used = {}, set()
    for col in df.columns:
        canon = _LOOKUP.get(_norm(col))
        if canon and canon not in used:
            mapping[col] = canon
            used.add(canon)
    return df.rename(columns=mapping)


def _to_number(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    cleaned = series.astype(str).str.replace(r"[^0-9.\-]", "", regex=True).replace("", np.nan)
    return pd.to_numeric(cleaned, errors="coerce")


def clean_data(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Validate and clean a raw sales table. Returns (clean_df, quality_report)."""
    if raw is None or raw.empty:
        raise DataValidationError("The file contains no rows.")

    report: dict = {
        "rows_raw": int(len(raw)), "duplicates_removed": 0, "invalid_dates_removed": 0,
        "invalid_rows_removed": 0, "values_imputed": {}, "columns_defaulted": [],
    }
    df = standardize_columns(raw.copy())
    present = set(df.columns)

    missing = []
    if "Order Date" not in present:
        missing.append("Order Date")
    if "Product" not in present:
        missing.append("Product")
    if "Revenue" not in present and not {"Quantity", "Unit Price"} <= present:
        missing.append("Revenue (or Quantity + Unit Price)")
    if "Cost" not in present and "Profit" not in present:
        missing.append("Cost (or Profit)")
    if missing:
        raise DataValidationError(
            "Missing required column(s): " + ", ".join(missing)
            + ". Found columns: " + ", ".join(map(str, raw.columns[:15]))
        )

    def note(col: str, n: int) -> None:
        if n and col in present:
            report["values_imputed"][col] = report["values_imputed"].get(col, 0) + int(n)

    # 1. Duplicates
    n0 = len(df)
    df = df.drop_duplicates().copy()
    report["duplicates_removed"] = int(n0 - len(df))

    # 2. Text columns
    text_cols = ["Order ID", "Customer ID", "Customer Name", "Product", "Category",
                 "Region", "State", "Customer Segment"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip().replace("", pd.NA)

    # 3. Dates
    try:
        df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce", format="mixed")
    except (TypeError, ValueError):  # older pandas without format="mixed"
        df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    bad = df["Order Date"].isna()
    report["invalid_dates_removed"] = int(bad.sum())
    df = df[~bad].copy()
    df["Order Date"] = df["Order Date"].dt.normalize()

    # 4. Numeric columns
    for col in ["Quantity", "Unit Price", "Revenue", "Cost", "Profit"]:
        if col in df.columns:
            df[col] = _to_number(df[col])

    if "Quantity" not in df.columns:
        df["Quantity"] = 1.0
        report["columns_defaulted"].append("Quantity (assumed 1 per row)")
    for col in ("Revenue", "Unit Price", "Cost", "Profit"):
        if col not in df.columns:
            df[col] = np.nan

    m = df["Quantity"].isna()
    if m.any():
        derived = df["Revenue"] / df["Unit Price"]
        df.loc[m, "Quantity"] = derived[m].replace([np.inf, -np.inf], np.nan).fillna(1.0).round().clip(lower=1)
        note("Quantity", m.sum())
    m = df["Revenue"].isna() & df["Unit Price"].notna()
    df.loc[m, "Revenue"] = (df["Quantity"] * df["Unit Price"])[m]
    note("Revenue", m.sum())
    m = df["Unit Price"].isna() & (df["Quantity"] > 0)
    df.loc[m, "Unit Price"] = (df["Revenue"] / df["Quantity"])[m]
    note("Unit Price", m.sum())

    m = df["Cost"].isna() & df["Profit"].notna() & df["Revenue"].notna()
    df.loc[m, "Cost"] = (df["Revenue"] - df["Profit"])[m]
    still = df["Cost"].isna() & df["Revenue"].notna()
    if still.any():
        ratio = (df["Cost"] / df["Revenue"]).replace([np.inf, -np.inf], np.nan).median()
        ratio = 0.7 if pd.isna(ratio) else float(ratio)
        df.loc[still, "Cost"] = df.loc[still, "Revenue"] * ratio
        note("Cost", still.sum())
    m = df["Profit"].isna()
    df.loc[m, "Profit"] = (df["Revenue"] - df["Cost"])[m]
    note("Profit", m.sum())

    # 5. Invalid rows
    bad = df["Revenue"].isna() | (df["Quantity"] <= 0) | (df["Revenue"] < 0)
    report["invalid_rows_removed"] = int(bad.sum())
    df = df[~bad].copy()
    if df.empty:
        raise DataValidationError("No valid rows remain after cleaning (check dates, quantities and revenue).")

    # 6. Identifiers and categorical defaults
    if "Customer ID" not in df.columns:
        if "Customer Name" in df.columns:
            codes = pd.factorize(df["Customer Name"].fillna("Unknown"))[0] + 1
            df["Customer ID"] = ["CUST-" + str(c).zfill(4) for c in codes]
            report["columns_defaulted"].append("Customer ID (generated from Customer Name)")
        else:
            df["Customer ID"] = "Unknown"
            report["columns_defaulted"].append("Customer ID (single unknown customer)")
    if "Customer Name" not in df.columns:
        df["Customer Name"] = df["Customer ID"]
    if "Order ID" not in df.columns:
        df["Order ID"] = ["ORD-" + str(i + 1).zfill(6) for i in range(len(df))]
        report["columns_defaulted"].append("Order ID (generated per row)")

    present = set(df.columns)
    n = df["Order ID"].isna().sum()
    if n:
        df.loc[df["Order ID"].isna(), "Order ID"] = ["ORD-X" + str(i).zfill(5) for i in range(int(n))]
        note("Order ID", n)
    df["Customer ID"] = df["Customer ID"].fillna("Unknown")
    df["Customer Name"] = df["Customer Name"].fillna(df["Customer ID"])

    defaults = {"Customer Segment": "Unassigned", "Category": "Uncategorized",
                "Region": "Unknown", "State": "Unknown", "Product": "Unknown"}
    for col, value in defaults.items():
        if col not in df.columns:
            df[col] = value
            report["columns_defaulted"].append(f"{col} (set to '{value}')")
        else:
            note(col, df[col].isna().sum())
            df[col] = df[col].fillna(value)

    for col in text_cols:
        df[col] = df[col].astype(str)
    df["Quantity"] = df["Quantity"].round().astype(int)
    for col in ["Unit Price", "Revenue", "Cost", "Profit"]:
        df[col] = df[col].astype(float).round(2)

    df = df[CANONICAL_COLUMNS].sort_values("Order Date").reset_index(drop=True)
    report["rows_clean"] = int(len(df))
    report["date_min"], report["date_max"] = df["Order Date"].min(), df["Order Date"].max()
    return df, report
