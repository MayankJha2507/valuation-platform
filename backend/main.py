"""Valuation Platform API — FastAPI entry point."""
import os
from datetime import date, timedelta

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

app = FastAPI(title="Valuation Platform API")

# Instantiated once at startup so it's ready for table queries later.
# `None` if env vars are missing — /db-health surfaces that as a clear error.
supabase: Client | None = (
    create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
    else None
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "valuation-platform-api"}


@app.get("/db-health")
def db_health():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return {
            "status": "error",
            "detail": "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in backend/.env",
        }
    try:
        resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/",
            headers={
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            },
            timeout=5.0,
        )
        if resp.status_code == 200:
            return {"status": "ok", "database": "connected"}
        return {
            "status": "error",
            "database": "unexpected_response",
            "http_status": resp.status_code,
        }
    except httpx.RequestError as e:
        return {
            "status": "error",
            "database": "connection_failed",
            "detail": str(e),
        }


def _fetch_prices_paginated(
    client: Client,
    stock_id: int,
    start_date: str,
    page_size: int = 1000,
) -> list[dict]:
    """Fetch all price rows for a stock on or after start_date.

    Paginates in page_size batches to work around Supabase PostgREST's
    server-side max-rows=1000 cap.
    """
    rows: list[dict] = []
    cursor = start_date
    while True:
        batch = (
            client.table("price_history")
            .select("date, open, high, low, close, adj_close, volume")
            .eq("stock_id", stock_id)
            .gte("date", cursor)
            .order("date", desc=False)
            .limit(page_size)
            .execute()
        )
        if not batch.data:
            break
        rows.extend(batch.data)
        if len(batch.data) < page_size:
            break  # Received a partial page — nothing more to fetch.
        # Advance cursor past the last returned date so the next page
        # doesn't re-fetch it.
        last = date.fromisoformat(batch.data[-1]["date"])
        cursor = (last + timedelta(days=1)).isoformat()
    return rows


@app.get("/stocks/{symbol}/prices")
def get_stock_prices(
    symbol: str,
    days: int = Query(default=365, ge=1, le=1825, description="Number of days of history to return (1–1825)"),
):
    """Return daily price history for an NSE symbol.

    - **symbol**: bare NSE symbol, e.g. RELIANCE, M%26M (URL-encoded &), BAJAJ-AUTO
    - **days**: how many calendar days back to look (default 365, max 1825 = 5 years)
    """
    if supabase is None:
        raise HTTPException(status_code=503, detail="Database client not initialised")

    symbol = symbol.upper()

    # Look up the stock — 404 if it's not in our Nifty 50 master list.
    # Use .limit(1) not .single(): .single() raises an exception on 0 rows
    # instead of returning empty data, which produces an unhandled 500.
    stock_result = (
        supabase.table("stocks")
        .select("id, nse_symbol, ticker, company_name, sector")
        .eq("nse_symbol", symbol)
        .limit(1)
        .execute()
    )
    if not stock_result.data:
        raise HTTPException(
            status_code=404,
            detail=f"Symbol '{symbol}' not found. Must be a valid Nifty 50 NSE symbol.",
        )
    stock = stock_result.data[0]
    start_date = (date.today() - timedelta(days=days)).isoformat()

    # Supabase's PostgREST enforces a server-side max-rows=1000 that overrides
    # any client-side .limit(). For requests spanning > ~1000 trading days we
    # use cursor-based pagination: multiple ≤1000-row requests advancing by
    # date, stitched into one response.
    price_rows = _fetch_prices_paginated(supabase, stock["id"], start_date)
    prices = type("R", (), {"data": price_rows})()

    return {
        "symbol": stock["nse_symbol"],
        "company_name": stock["company_name"],
        "ticker": stock["ticker"],
        "sector": stock["sector"],
        "days_requested": days,
        "rows": len(prices.data),
        "date_from": prices.data[0]["date"] if prices.data else None,
        "date_to": prices.data[-1]["date"] if prices.data else None,
        "prices": prices.data,
    }


@app.get("/db-tables")
def db_tables():
    """Verify each expected table exists by attempting a 1-row read."""
    if supabase is None:
        return {"status": "error", "detail": "Supabase client not initialized"}
    expected = ["stocks", "price_history", "financials", "valuations"]
    results: dict[str, dict] = {}
    all_ok = True
    for name in expected:
        try:
            supabase.table(name).select("id").limit(1).execute()
            results[name] = {"status": "exists"}
        except Exception as e:
            all_ok = False
            results[name] = {
                "status": "missing",
                "error_class": e.__class__.__name__,
                "detail": str(e)[:300],
            }
    return {"status": "ok" if all_ok else "error", "tables": results}
