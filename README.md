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
├── backend/          FastAPI app — valuation logic, data fetching, API
│   ├── .venv/        Python virtual environment (gitignored)
│   ├── main.py       FastAPI entry point
│   └── requirements.txt
├── frontend/         Next.js app (not yet scaffolded)
├── docs/
│   └── PRD.md        Product requirements (placeholder)
├── DECISIONS.md      Running log of technical/product decisions
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

## Status

Foundation scaffolded. No application logic yet — just a `/health` endpoint to confirm the server runs.
