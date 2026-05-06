# Valuation Platform

A web app to help Indian retail investors evaluate Nifty 50 stocks. Users search for a stock and see a valuation analysis — intrinsic value, key ratios, sector and historical comparisons, and a plain-English verdict on whether the stock is **Undervalued**, **Fairly Valued**, or **Overvalued**.

## What you'll see per stock

- Current price, sector, market cap
- Discounted Cash Flow (DCF) intrinsic value estimate
- Key valuation ratios: P/E, P/B, EV/EBITDA, P/S, PEG
- Comparison vs. sector average and the stock's own 5-year history
- Weighted verdict (Undervalued / Fairly Valued / Overvalued) with a plain-English explanation
- Price chart (1Y, 3Y, 5Y)

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js, Tailwind CSS, shadcn/ui |
| Backend | Python 3.13, FastAPI |
| Database | PostgreSQL (Supabase, free tier) |
| Market data | `yfinance`, `jugaad-data` |
| Hosting (later) | Render (backend), Netlify (frontend) |

## Project structure

```
valuation-platform/
├── backend/
│   ├── data/
│   │   ├── fetch_prices.py     fetches OHLCV from yfinance → Supabase
│   │   └── fetch_financials.py fetches income / balance / cashflow → Supabase
│   ├── scripts/
│   │   ├── seed_nifty50.py     one-off: seeds stocks table with Nifty 50
│   │   └── fetch_all_prices.py one-off: fetches prices for all 50 stocks
│   ├── sql/
│   │   ├── 001_initial_schema.sql
│   │   └── 002_grants.sql
│   ├── .venv/                  Python virtual environment (gitignored)
│   ├── .env.example            credential template (copy → .env, fill values)
│   ├── main.py                 FastAPI entry point + all API endpoints
│   └── requirements.txt
├── frontend/                   Next.js app (not yet scaffolded)
├── docs/
│   └── PRD.md
├── DECISIONS.md                running log of technical/product decisions
├── README.md
└── .gitignore
```

## Running the backend locally

You need **Python 3.13+** installed. From the project root:

```bash
cd backend
.venv/bin/uvicorn main:app --reload
```

Then open http://localhost:8000/health in your browser. You should see:

```json
{"status": "ok", "service": "valuation-platform-api"}
```

The `--reload` flag makes the server restart automatically when you save changes to Python files. Press **Ctrl+C** in the terminal to stop it.

### First-time setup (if `.venv/` is missing)

This only applies if someone clones the repo fresh:

```bash
cd backend
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Confirms the server is running |
| GET | `/db-health` | Confirms Supabase connection is live |
| GET | `/db-tables` | Verifies all 4 expected tables exist |
| GET | `/stocks/{symbol}/prices` | Price history for an NSE symbol |
| GET | `/stocks/{symbol}/financials` | Annual + quarterly financials |

### `/stocks/{symbol}/prices`

- **symbol** — NSE symbol, e.g. `RELIANCE`, `BAJAJ-AUTO`, `M%26M` (URL-encode `&` as `%26`)
- **days** — query param, 1–1825 (default 365). Returns that many calendar days of history.

```bash
# Last year of RELIANCE prices
curl http://localhost:8000/stocks/RELIANCE/prices

# Full 5 years for M&M (& must be URL-encoded)
curl "http://localhost:8000/stocks/M%26M/prices?days=1825"
```

Response shape:
```json
{
  "symbol": "RELIANCE",
  "company_name": "Reliance Industries Ltd.",
  "ticker": "RELIANCE.NS",
  "sector": "Oil Gas & Consumable Fuels",
  "days_requested": 365,
  "rows": 247,
  "date_from": "2025-05-05",
  "date_to": "2026-04-30",
  "prices": [
    { "date": "2025-05-05", "open": 1431.0, "high": 1439.5, "low": 1426.9,
      "close": 1431.3, "adj_close": 1425.61, "volume": 12685649 }
  ]
}
```

## Status

- ✅ FastAPI backend running with Supabase connection
- ✅ Database schema: `stocks`, `price_history`, `financials`, `valuations`
- ✅ Nifty 50 master list seeded (50 stocks)
- ✅ Price history fetched for all 50 Nifty stocks (~60,000 rows)
- ✅ `/stocks/{symbol}/prices` endpoint with 5-year support and pagination
- ✅ Financials fetched for RELIANCE, TCS, HDFCBANK (annual + quarterly)
- ✅ `/stocks/{symbol}/financials` endpoint (annual / quarterly / both)
- 🔲 Financials fetch for all 50 stocks — next session
- 🔲 Valuation engine (DCF + ratios) — upcoming
- 🔲 Frontend (Next.js) — upcoming
