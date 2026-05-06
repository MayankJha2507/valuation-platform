"""Fetch quarterly and annual financials from yfinance → upsert into financials table.

yfinance returns three separate DataFrames per period type:
  - .financials / .quarterly_financials     (income statement)
  - .balance_sheet / .quarterly_balance_sheet
  - .cashflow / .quarterly_cashflow

Each DataFrame has metrics as rows (index) and period-end dates as columns.
We iterate over dates in the income statement DataFrame, pull matching rows from
the balance sheet and cashflow (by date), and combine into one DB row.

Fiscal year/quarter mapping (Indian FY runs April → March):
  - Period ending Jan/Feb/Mar → fiscal_quarter=4, fiscal_year=that calendar year
  - Period ending Apr/May/Jun → fiscal_quarter=1, fiscal_year=calendar_year+1
  - Period ending Jul/Aug/Sep → fiscal_quarter=2, fiscal_year=calendar_year+1
  - Period ending Oct/Nov/Dec → fiscal_quarter=3, fiscal_year=calendar_year+1

Run from backend/ directory:
    .venv/bin/python data/fetch_financials.py RELIANCE
"""
from __future__ import annotations

import os
import sys
from datetime import date

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


def _get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(df: pd.DataFrame | None, col, field: str) -> float | None:
    """Safely extract one value from a yfinance DataFrame.

    Returns None if the DataFrame is empty, the field (row) doesn't exist,
    the date (column) doesn't exist, or the value is NaN.
    """
    if df is None or df.empty:
        return None
    if field not in df.index:
        return None
    if col not in df.columns:
        return None
    val = df.at[field, col]
    return None if pd.isna(val) else float(val)


def _fiscal_period(period_end: date, period_type: str) -> tuple[int, int | None]:
    """Return (fiscal_year, fiscal_quarter) for an Indian-FY period-end date."""
    m, y = period_end.month, period_end.year
    # FY year = calendar year in which the March quarter falls
    fiscal_year = y if m <= 3 else y + 1
    if period_type == "annual":
        return fiscal_year, None
    quarter = {1: 4, 2: 4, 3: 4, 4: 1, 5: 1, 6: 1,
               7: 2, 8: 2, 9: 2, 10: 3, 11: 3, 12: 3}[m]
    return fiscal_year, quarter


def _build_rows(
    income: pd.DataFrame,
    balance: pd.DataFrame,
    cashflow: pd.DataFrame,
    stock_id: int,
    period_type: str,
) -> list[dict]:
    """Combine income / balance / cashflow into DB rows for one period type."""
    if income is None or income.empty:
        return []

    rows: list[dict] = []
    for col in income.columns:
        period_end = col.date() if hasattr(col, "date") else date.fromisoformat(str(col)[:10])
        fiscal_year, fiscal_quarter = _fiscal_period(period_end, period_type)

        g = lambda df, field: _get(df, col, field)  # noqa: E731

        rows.append({
            "stock_id": stock_id,
            "period_type": period_type,
            "period_end_date": period_end.isoformat(),
            "fiscal_year": fiscal_year,
            "fiscal_quarter": fiscal_quarter,
            # Income statement
            "revenue":          g(income, "Total Revenue"),
            "gross_profit":     g(income, "Gross Profit"),
            "operating_income": g(income, "Operating Income"),
            "net_income":       g(income, "Net Income"),
            "eps": (
                g(income, "Diluted EPS") or g(income, "Basic EPS")
            ),
            # Balance sheet
            "total_assets":      g(balance, "Total Assets"),
            "total_liabilities": g(balance, "Total Liabilities Net Minority Interest"),
            "total_equity":      g(balance, "Stockholders Equity"),
            "cash_and_equivalents": (
                g(balance, "Cash And Cash Equivalents")
                or g(balance, "Cash Cash Equivalents And Short Term Investments")
            ),
            "total_debt":         g(balance, "Total Debt"),
            "shares_outstanding": g(balance, "Ordinary Shares Number"),
            # Cash flow
            "operating_cash_flow": g(cashflow, "Operating Cash Flow"),
            "capital_expenditure": g(cashflow, "Capital Expenditure"),
            "free_cash_flow":      g(cashflow, "Free Cash Flow"),
        })

    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_and_store_financials(nse_symbol: str) -> dict:
    """Fetch annual + quarterly financials for `nse_symbol` and upsert into DB.

    Args:
        nse_symbol: Bare NSE symbol, e.g. "RELIANCE", "TCS".

    Returns:
        Summary dict with symbol, annual_rows, quarterly_rows.

    Raises:
        ValueError: Symbol not found in the stocks table.
        RuntimeError: yfinance returned no financial data at all.
    """
    client = _get_supabase()

    # Look up stock_id
    result = (
        client.table("stocks")
        .select("id, ticker, company_name")
        .eq("nse_symbol", nse_symbol)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise ValueError(f"Symbol '{nse_symbol}' not found in stocks table.")
    stock_id: int = result.data[0]["id"]
    ticker: str = result.data[0]["ticker"]
    company: str = result.data[0]["company_name"]

    print(f"Fetching financials for {company} ({ticker}) ...")

    t = yf.Ticker(ticker)

    # Build rows for both period types
    annual_rows = _build_rows(
        t.financials, t.balance_sheet, t.cashflow, stock_id, "annual"
    )
    quarterly_rows = _build_rows(
        t.quarterly_financials, t.quarterly_balance_sheet,
        t.quarterly_cashflow, stock_id, "quarterly"
    )

    all_rows = annual_rows + quarterly_rows
    if not all_rows:
        raise RuntimeError(f"yfinance returned no financial data for {ticker}.")

    # Upsert — conflict on (stock_id, period_type, period_end_date)
    client.table("financials").upsert(
        all_rows, on_conflict="stock_id,period_type,period_end_date"
    ).execute()

    print(f"  Annual rows:    {len(annual_rows)}")
    print(f"  Quarterly rows: {len(quarterly_rows)}")
    print(f"  Total upserted: {len(all_rows)}")

    return {
        "symbol": nse_symbol,
        "ticker": ticker,
        "stock_id": stock_id,
        "annual_rows": len(annual_rows),
        "quarterly_rows": len(quarterly_rows),
        "total_upserted": len(all_rows),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: fetch_financials.py <NSE_SYMBOL>")
    result = fetch_and_store_financials(sys.argv[1].upper())
    print("\nSummary:", result)
