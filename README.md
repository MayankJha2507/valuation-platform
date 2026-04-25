# Valuation Platform

A web app to help retail investors evaluate Indian stocks. Users search for a stock and see its valuation analysis — intrinsic value, key ratios, sector and historical comparisons, and a plain-English verdict on whether the stock is **Undervalued**, **Fairly Valued**, or **Overvalued**.

## MVP scope

- **Coverage:** Nifty 50 stocks only
- **Inputs:** Stock ticker / company name
- **Outputs per stock:**
  - Discounted Cash Flow (DCF) intrinsic value
  - Key valuation ratios: P/E, P/B, EV/EBITDA, P/S, PEG
  - Comparison vs. sector average and the stock's own historical averages
  - Plain-English verdict (Undervalued / Fairly Valued / Overvalued)

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js, Tailwind CSS, shadcn/ui |
| Backend | Python, FastAPI |
| Database | PostgreSQL (hosted on Supabase, free tier) |
| Market data | `yfinance`, `jugaad-data` |
| Hosting (later) | Render (backend), Netlify (frontend) |

## Project structure

```
valuation-platform/
├── backend/    # FastAPI app — valuation logic, data fetching, API endpoints
├── frontend/   # Next.js app — UI, search, results display
└── README.md
```

## Status

Foundation setup in progress. No application code yet.
