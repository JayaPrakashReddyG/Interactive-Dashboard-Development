# Interactive Business Analytics Dashboard

A multi-page business intelligence dashboard built with **Python, Streamlit and Plotly**. It turns a sales
dataset (built-in sample, CSV or Excel upload) into KPIs, trends, customer and product analysis, regional
comparisons and automatically generated business insights. Built as a Data Analytics internship project.

## Features

| Page | What it answers |
|---|---|
| **Executive Overview** | Revenue, orders, customers, AOV, revenue growth and profit margin with previous-period comparison and a growth-target indicator, trend chart, category/region mix, auto-generated insights and recommendations |
| **Sales Analysis** | Daily / weekly / monthly / yearly trends, year-over-year comparison, revenue by category and region, top 10 products, sales vs profit, monthly table with MoM change |
| **Customer Analytics** | Unique customers, new vs returning, RFM value segments, segment revenue, top customers, orders-per-customer distribution |
| **Product Performance** | Best and lowest sellers, category revenue, units sold, profit contribution, revenue-vs-margin matrix, declining and growing products, optional correlation analysis |
| **Regional Analysis** | Region and state revenue and profit, High / Average / Low performance tiers, region x category heatmap, regional trends |

Also included: date range, region, category and segment filters with a **Reset filters** button; CSV and Excel
upload with automatic validation (duplicates, bad dates, wrong types, missing values); downloadable filtered
data (CSV), analytical report (Excel, 9 sheets) and summary report (Markdown). All figures are computed from
the records; nothing is hard-coded.

## Technology stack

Python 3.10+, Streamlit, Pandas, NumPy, Plotly, Matplotlib and Seaborn (optional statistics), OpenPyXL.

## Project structure

```
interactive-business-analytics-dashboard/
├── app.py                  # entry point: page config, navigation, sidebar context
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/config.toml  # dark theme
├── data/sample_sales_data.csv
├── assets/style.css
├── components/             # sidebar.py, kpi_cards.py, charts.py, insights.py
├── utils/                  # data_loader.py, data_cleaning.py, calculations.py
└── pages/                  # 1_Executive_Overview.py ... 5_Regional_Analysis.py
```

## Installation (Windows PowerShell)

```powershell
cd path\to\interactive-business-analytics-dashboard
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m streamlit run app.py
```

If activation is blocked, run once: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.
The app opens at http://localhost:8501.

## Running in VS Code

1. **File > Open Folder** and choose `interactive-business-analytics-dashboard`.
2. `Ctrl+Shift+P` > **Python: Select Interpreter** > choose `.venv`.
3. Open the terminal (`Ctrl+``) and run `python -m streamlit run app.py`.

## Using your own data

Choose **Upload CSV / Excel** in the sidebar. Column names are matched flexibly (for example `Qty`, `Sales`,
`Total Cost`). Required: Order Date, Product, Revenue (or Quantity + Unit Price) and Cost (or Profit).
Optional: Order ID, Customer ID / Name, Category, Region, State, Customer Segment (defaults are applied
and reported on the Executive Overview under *Data quality report*).

## Screenshots

Run the app, open each page and save a screenshot into `assets/screenshots/` (for example
`executive-overview.png`). Then reference it here with `![Executive Overview](assets/screenshots/executive-overview.png)`.

## Push to GitHub

```powershell
git init
git add .
git commit -m "Interactive Business Analytics Dashboard"
git branch -M main
git remote add origin https://github.com/<your-username>/interactive-business-analytics-dashboard.git
git push -u origin main
```

## Deploy on Streamlit Community Cloud

1. Push the project to a public GitHub repository (above).
2. Sign in at https://share.streamlit.io with GitHub and click **Create app**.
3. Select the repository, branch `main` and main file path `app.py`.
4. Click **Deploy**. Dependencies install automatically from `requirements.txt`.

## Troubleshooting

| Problem | Fix |
|---|---|
| `streamlit` is not recognised | Activate the venv, then use `python -m streamlit run app.py` |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` inside the activated venv |
| Script execution disabled | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` |
| Port 8501 in use | `python -m streamlit run app.py --server.port 8502` |
| Upload rejected | Read the message in the sidebar; it lists the missing required columns |
| "No records match the filters" | Press **Reset filters** or widen the date range |
| Page looks unstyled | Run from the project root so `assets/style.css` and `.streamlit/` are found |
| Delete cached data | Press `C` in the app, then *Clear cache*, or restart Streamlit |

## Data design note

The sample dataset (4,000 orders, 450 customers, 24 products, 2024-2025) is synthetic and regenerated
by `utils/data_loader.py::generate_sample_data` if the CSV is missing. It includes growth, seasonality and a
few deliberately declining products so the insights have something to find.
