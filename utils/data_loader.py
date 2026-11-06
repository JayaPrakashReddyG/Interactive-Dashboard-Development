"""Dataset sources: built-in synthetic sample data and CSV / Excel uploads."""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from utils.data_cleaning import clean_data

SAMPLE_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_sales_data.csv"

# category -> (product, list price, cost as share of price)
CATALOG = {
    "Technology": [("Laptop Pro 15", 1250, 0.78), ("Wireless Headset", 140, 0.55), ("4K Monitor 27in", 420, 0.70),
                   ("Mechanical Keyboard", 110, 0.50), ("Webcam HD", 85, 0.52)],
    "Furniture": [("Standing Desk", 620, 0.66), ("Ergonomic Chair", 380, 0.62), ("Bookshelf Oak", 210, 0.64),
                  ("Filing Cabinet", 175, 0.68), ("Desk Lamp LED", 45, 0.45)],
    "Office Supplies": [("Printer Paper Case", 38, 0.72), ("Gel Pen Box", 14, 0.40), ("Binder Set", 22, 0.48),
                        ("Label Maker", 58, 0.55), ("Whiteboard 4ft", 120, 0.60)],
    "Software": [("Analytics Suite License", 900, 0.25), ("Antivirus 1yr", 60, 0.30),
                 ("Design Toolkit", 340, 0.28), ("Cloud Backup Plan", 150, 0.32)],
    "Accessories": [("USB-C Hub", 55, 0.50), ("Laptop Sleeve", 35, 0.46), ("Wireless Mouse", 48, 0.52),
                    ("Phone Stand", 22, 0.42), ("Cable Organizer", 15, 0.38)],
}
REGIONS = {
    "West": ["California", "Washington", "Oregon"],
    "East": ["New York", "Massachusetts", "Pennsylvania"],
    "South": ["Texas", "Florida", "Georgia"],
    "Central": ["Colorado", "Missouri", "Ohio"],
    "North": ["Illinois", "Michigan", "Minnesota"],
}
REGION_WEIGHTS = [0.28, 0.26, 0.22, 0.14, 0.10]
# Share change in order volume across the two years (negative = declining product)
PRODUCT_TREND = {
    "Printer Paper Case": -0.7, "Webcam HD": -0.6, "Filing Cabinet": -0.5, "Binder Set": -0.4,
    "Cloud Backup Plan": 1.2, "Wireless Headset": 0.9, "Standing Desk": 0.8, "Analytics Suite License": 0.6,
}
FIRST = ["Olivia", "Liam", "Emma", "Noah", "Ava", "Ethan", "Sophia", "Mason", "Isabella", "Lucas",
         "Mia", "Logan", "Amelia", "James", "Harper", "Elijah", "Evelyn", "Henry", "Ella", "Jack"]
LAST = ["Anderson", "Brooks", "Carter", "Diaz", "Ellis", "Foster", "Grant", "Hayes", "Irwin", "Jensen",
        "Kim", "Lopez", "Morgan", "Nguyen", "Ortiz", "Patel", "Quinn", "Reyes", "Shaw", "Turner",
        "Underwood", "Vega", "Walsh", "Young", "Zhang"]


def generate_sample_data(n_orders: int = 4000, seed: int = 42) -> pd.DataFrame:
    """Create a realistic synthetic sales dataset (growth, seasonality, declining products)."""
    rng = np.random.default_rng(seed)
    days = pd.date_range("2024-01-01", "2025-12-31", freq="D")
    t = np.arange(len(days))
    weight = (1 + 0.30 * np.sin(2 * np.pi * (days.dayofyear.to_numpy() - 80) / 365)
              + np.where(days.month >= 11, 0.25, 0.0)) * (1 + 0.0006 * t) * np.where(days.dayofweek >= 5, 0.6, 1.0)
    day_idx = np.sort(rng.choice(len(days), size=n_orders, p=weight / weight.sum()))

    n_cust = 450
    combos = rng.choice(len(FIRST) * len(LAST), n_cust, replace=False)
    names = [f"{FIRST[c // len(LAST)]} {LAST[c % len(LAST)]}" for c in combos]
    segments = rng.choice(["Consumer", "Corporate", "Small Business", "Enterprise"], n_cust, p=[0.40, 0.25, 0.25, 0.10])
    region_names = list(REGIONS)
    cust_region = rng.choice(region_names, n_cust, p=REGION_WEIGHTS)
    cust_state = [rng.choice(REGIONS[r]) for r in cust_region]
    activity = rng.gamma(1.2, 1.0, n_cust)
    join_day = rng.integers(0, 600, n_cust)
    join_day[: int(0.3 * n_cust)] = 0

    items = [(cat, p, price, ratio) for cat, lst in CATALOG.items() for p, price, ratio in lst]
    base_w = np.array([price ** -0.4 * rng.uniform(0.8, 1.2) for _, _, price, _ in items])
    slope = np.array([PRODUCT_TREND.get(p, 0.0) for _, p, _, _ in items])
    qty_mult = {"Consumer": 1.0, "Small Business": 1.2, "Corporate": 1.6, "Enterprise": 2.2}

    rows = []
    for i, d in enumerate(day_idx):
        eligible = np.where(join_day <= d)[0]
        c = rng.choice(eligible, p=activity[eligible] / activity[eligible].sum())
        w = base_w * np.clip(1 + slope * d / len(days), 0.15, None)
        cat, product, price, ratio = items[rng.choice(len(items), p=w / w.sum())]
        max_q = 3 if price > 500 else 6 if price > 100 else 12
        qty = max(1, int(round(rng.integers(1, max_q + 1) * qty_mult[segments[c]])))
        unit_price = round(price * rng.uniform(0.93, 1.07) * (1 - rng.choice([0, 0, 0, 0.05, 0.10, 0.15])), 2)
        revenue = round(qty * unit_price, 2)
        cost = round(qty * price * ratio * rng.uniform(0.95, 1.05), 2)
        rows.append({
            "Order ID": f"ORD-{i + 1:06d}", "Order Date": days[d].strftime("%Y-%m-%d"),
            "Customer ID": f"CUST-{c + 1:04d}", "Customer Name": names[c], "Product": product,
            "Category": cat, "Region": cust_region[c], "State": cust_state[c], "Quantity": qty,
            "Unit Price": unit_price, "Revenue": revenue, "Cost": cost, "Profit": round(revenue - cost, 2),
            "Customer Segment": segments[c],
        })
    return pd.DataFrame(rows)


def read_sample_raw() -> pd.DataFrame:
    """Read the bundled sample CSV, regenerating it if the file is missing."""
    if not SAMPLE_PATH.exists():
        SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        generate_sample_data().to_csv(SAMPLE_PATH, index=False)
    return pd.read_csv(SAMPLE_PATH)


def read_uploaded(name: str, content: bytes) -> pd.DataFrame:
    """Parse an uploaded CSV or Excel file into a raw DataFrame."""
    ext = Path(name).suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        return pd.read_excel(io.BytesIO(content), engine="openpyxl")
    if ext in (".csv", ".txt"):
        for encoding in ("utf-8-sig", "latin-1"):
            try:
                return pd.read_csv(io.BytesIO(content), sep=None, engine="python", encoding=encoding)
            except UnicodeDecodeError:
                continue
    raise ValueError("Unsupported file type. Upload a .csv or .xlsx file.")


@st.cache_data(show_spinner=False)
def load_sample_data() -> tuple[pd.DataFrame, dict]:
    return clean_data(read_sample_raw())


@st.cache_data(show_spinner="Reading and validating file...")
def load_uploaded_data(name: str, content: bytes) -> tuple[pd.DataFrame, dict]:
    return clean_data(read_uploaded(name, content))
