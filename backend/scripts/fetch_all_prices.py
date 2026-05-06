"""Fetch 5 years of daily price history for every active Nifty 50 stock.

Run from the backend/ directory:
    .venv/bin/python scripts/fetch_all_prices.py

What it does:
  - Reads all active symbols from the stocks table.
  - Calls fetch_and_store_prices() for each, with a 1-second pause between
    calls to stay within yfinance / Yahoo Finance rate limits.
  - Skips stocks that fail and reports them at the end.
  - Safe to re-run: the underlying upsert updates existing rows.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from dotenv import load_dotenv
from supabase import create_client

from data.fetch_prices import fetch_and_store_prices

load_dotenv()

SLEEP_BETWEEN_CALLS = 1.0  # seconds — avoids Yahoo Finance rate-limiting

supabase = create_client(
    os.getenv("SUPABASE_URL", ""),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
)


def main() -> None:
    symbols: list[str] = [
        r["nse_symbol"]
        for r in supabase.table("stocks")
        .select("nse_symbol")
        .eq("is_active", True)
        .order("nse_symbol")
        .execute()
        .data
    ]

    print(f"Fetching prices for {len(symbols)} stocks...\n")

    success: list[str] = []
    failed: list[tuple[str, str]] = []
    total_rows = 0

    for i, symbol in enumerate(symbols, 1):
        print(f"[{i:2d}/{len(symbols)}] {symbol}")
        try:
            result = fetch_and_store_prices(symbol, years=5)
            total_rows += result["rows_upserted"]
            success.append(symbol)
        except Exception as e:
            print(f"        FAILED: {e.__class__.__name__}: {e}")
            failed.append((symbol, str(e)))

        if i < len(symbols):
            time.sleep(SLEEP_BETWEEN_CALLS)

    print(f"\n{'='*50}")
    print(f"Done. {len(success)}/{len(symbols)} stocks succeeded.")
    print(f"Total rows upserted: {total_rows:,}")
    if failed:
        print(f"\nFailed ({len(failed)}):")
        for sym, err in failed:
            print(f"  {sym}: {err[:80]}")
    print("="*50)


if __name__ == "__main__":
    main()
