"""Fetch daily OHLCV price data from yfinance and upsert into price_history.

Design decisions (see DECISIONS.md 2026-05-03):
- 5 years of history by default.
- auto_adjust=False so we get both `close` (actual traded price) and
  `adj_close` (split/dividend adjusted). All analysis should use adj_close.
- Dates stored as plain DATE strings (YYYY-MM-DD) representing the IST
  trading session date. No timezone math needed.
- Upserts in batches of 500 rows so large fetches don't hit payload limits.
- Idempotent: re-running updates existing rows rather than duplicating them.
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

BATCH_SIZE = 500  # rows per Supabase upsert call


def _get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
    return create_client(url, key)


def fetch_and_store_prices(nse_symbol: str, years: int = 5) -> dict:
    """Fetch `years` of daily OHLCV for `nse_symbol` and upsert into price_history.

    Args:
        nse_symbol: Bare NSE symbol, e.g. "RELIANCE", "M&M", "BAJAJ-AUTO".
        years: How many years of history to fetch (default 5).

    Returns:
        Summary dict with symbol, row counts, and date range.

    Raises:
        ValueError: Symbol not found in the stocks table.
        RuntimeError: yfinance returned no data.
    """
    client = _get_supabase()

    # --- 1. Look up stock_id from the stocks table ---
    result = (
        client.table("stocks")
        .select("id, ticker, company_name")
        .eq("nse_symbol", nse_symbol)
        .single()
        .execute()
    )
    if not result.data:
        raise ValueError(
            f"Symbol '{nse_symbol}' not found in stocks table. "
            "Check that it's a valid Nifty 50 NSE symbol."
        )
    stock_id: int = result.data["id"]
    ticker: str = result.data["ticker"]          # e.g. "RELIANCE.NS"
    company: str = result.data["company_name"]

    print(f"Fetching {years}y of prices for {company} ({ticker}) ...")

    # --- 2. Fetch from yfinance ---
    end_date = date.today()
    start_date = end_date - timedelta(days=years * 365)

    # auto_adjust=False gives us both Close (unadjusted) and Adj Close.
    hist: pd.DataFrame = yf.Ticker(ticker).history(
        start=start_date.isoformat(),
        end=end_date.isoformat(),
        auto_adjust=False,
    )

    if hist.empty:
        raise RuntimeError(
            f"yfinance returned no data for {ticker}. "
            "The ticker may be delisted or there may be a network issue."
        )

    # --- 3. Transform into rows matching price_history schema ---
    # hist.index is a DatetimeIndex. str(ts)[:10] gives "YYYY-MM-DD" (IST date).
    rows: list[dict] = []
    for ts, row in hist.iterrows():
        rows.append(
            {
                "stock_id": stock_id,
                "date": str(ts)[:10],
                "open": _safe_float(row.get("Open")),
                "high": _safe_float(row.get("High")),
                "low": _safe_float(row.get("Low")),
                "close": _safe_float(row.get("Close")),
                "adj_close": _safe_float(row.get("Adj Close")),
                "volume": _safe_int(row.get("Volume")),
            }
        )

    print(f"  yfinance returned {len(rows)} rows "
          f"({rows[0]['date']} → {rows[-1]['date']})")

    # --- 4. Upsert in batches of BATCH_SIZE ---
    # on_conflict matches the UNIQUE constraint (stock_id, date) so re-runs
    # update existing rows instead of raising a duplicate-key error.
    total_upserted = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        client.table("price_history").upsert(
            batch, on_conflict="stock_id,date"
        ).execute()
        total_upserted += len(batch)
        print(f"  Upserted batch {i // BATCH_SIZE + 1}: {total_upserted}/{len(rows)} rows")

    summary = {
        "symbol": nse_symbol,
        "ticker": ticker,
        "stock_id": stock_id,
        "rows_fetched": len(rows),
        "rows_upserted": total_upserted,
        "date_from": rows[0]["date"],
        "date_to": rows[-1]["date"],
    }
    print(f"  Done. {total_upserted} rows upserted.")
    return summary


def _safe_float(val) -> float | None:
    """Return float or None for NaN/None values."""
    try:
        f = float(val)
        return None if pd.isna(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


def _safe_int(val) -> int | None:
    """Return int or None for NaN/None values."""
    try:
        f = float(val)
        return None if pd.isna(f) else int(f)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# CLI entry point: run directly to fetch a single stock
#   .venv/bin/python data/fetch_prices.py RELIANCE
#   .venv/bin/python data/fetch_prices.py RELIANCE 3     ← 3 years only
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit("Usage: fetch_prices.py <NSE_SYMBOL> [years]")
    sym = args[0].upper()
    yrs = int(args[1]) if len(args) > 1 else 5
    result = fetch_and_store_prices(sym, years=yrs)
    print("\nSummary:", result)
