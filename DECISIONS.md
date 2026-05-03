# Decisions Log

A running log of meaningful technical and product decisions, why they were made, and what they imply.

Format per entry:
- **Date** — short title
- **Context:** what prompted the decision
- **Decision:** what was chosen
- **Why:** the reasoning / tradeoff
- **Implications:** what this locks in, what it leaves open

---

## 2026-05-02 — Tech stack chosen for MVP

- **Context:** Need to ship an MVP web app that retail investors can use to evaluate Nifty 50 stocks.
- **Decision:** Python 3.13 + FastAPI (backend), Next.js + Tailwind + shadcn/ui (frontend), PostgreSQL via Supabase free tier (database), `yfinance` + `jugaad-data` (market data), Render + Netlify (hosting, later).
- **Why:** Familiar, modern stack with strong free-tier hosting. FastAPI is fast to develop with and well-documented. Supabase removes Postgres ops. yfinance + jugaad-data are the practical free options for Indian market data.
- **Implications:** We're tied to free-tier limits (rate limits, cold starts on Render). Data quality depends on yfinance/jugaad-data — need to verify accuracy as we go.

---

## 2026-05-02 — Python 3.13, not 3.9

- **Context:** Originally started on macOS system Python 3.9.6; that's past end-of-life.
- **Decision:** Upgraded to Python 3.13.13.
- **Why:** Modern libraries are dropping 3.9 support; 3.13 gets security updates and is what tutorials target.
- **Implications:** No version-pinning gymnastics for old libs. If we deploy to Render later, we'll specify Python 3.13 in the runtime config.

---

## 2026-05-02 — Always include explicit GRANTs in migrations

- **Context:** First migration (001_initial_schema.sql) set up tables + RLS policies but no GRANT statements. Even the `service_role` key got "permission denied" (Postgres error 42501).
- **Decision:** Add explicit `GRANT` statements in every migration that touches schema. Don't rely on Supabase's default privileges.
- **Why:** Supabase has two independent permission gates: (1) GRANT — can this role touch the table at all, (2) RLS — which rows can it see. Recent Supabase projects no longer auto-grant on new public-schema tables, so RLS policies alone aren't enough. Without GRANT, the request is rejected before RLS even runs.
- **Implications:** Every future migration that creates a table needs corresponding `GRANT ALL ... TO service_role` and `GRANT SELECT ... TO anon, authenticated` (or whichever subset matches the access intent). Documented in 002_grants.sql.

---

## 2026-05-03 — yfinance ticker format for NSE stocks

- **Context:** Two Nifty 50 symbols contain special characters (`M&M`, `BAJAJ-AUTO`). Needed to confirm yfinance handles them before committing to the pipeline.
- **Decision:** Use the raw NSE symbol with `.NS` suffix as-is: `M&M.NS`, `BAJAJ-AUTO.NS`. No mapping or escaping required.
- **Why:** yfinance 1.3.0 tested successfully for all three representative tickers (`RELIANCE.NS`, `M&M.NS`, `BAJAJ-AUTO.NS`) — all returned valid price data. No special handling needed.
- **Implications:** Our `ticker` column in the `stocks` table stores the yfinance-ready format (e.g. `M&M.NS`). If a future stock in the Nifty 50 has a different convention, we'd revisit. The two currently affected symbols are confirmed working.

---

## 2026-05-03 — Price history data scope (4 decisions)

- **Context:** Starting to fetch real price data from yfinance. Needed to lock in scope before writing any pipeline code.

- **Decision 1 — Years of history: 5 years.**
  - Covers all three chart views (1Y, 3Y, 5Y) and the 5-year average ratios in our valuation schema.
  - ~1,250 trading days × 50 stocks = ~62,500 rows. Tiny for Postgres.
  - Misses the COVID crash (March 2020 is ~6 years ago). Acceptable for MVP; extend later by re-running fetch with `years=7`.

- **Decision 2 — Adjusted vs unadjusted: store both, use `adj_close` for all analysis.**
  - `adj_close` accounts for stock splits and dividends — essential for correct charts and historical ratio comparisons.
  - `close` is the actual traded price on the day — stored for reference.
  - Fetched with `auto_adjust=False` so yfinance returns both columns.
  - Rule: all ratio calculations and charts use `adj_close`. Only show `close` if displaying "actual price on that date."

- **Decision 3 — Gaps and missing data: store what yfinance returns; no gap-filling.**
  - NSE has ~15–20 holidays per year — missing rows on those dates is correct behavior.
  - Re-running the fetch script fills any gaps via upsert (idempotent).
  - Nifty 50 delistings are extremely unlikely for MVP; if a stock leaves the index, set `is_active=false` in `stocks` — historical price rows stay.
  - Step 4 sanity check is the safety net for data quality issues.

- **Decision 4 — Timezone: plain `DATE` = IST trading date; no timezone math.**
  - `price_history.date` is a Postgres `DATE` — no time component, no ambiguity.
  - yfinance labels each row by the NSE session date in IST. We strip the time and store the date as-is.
  - Never store UTC midnight timestamps that would shift to the wrong date when read back in IST.

---

<!-- Add new entries above this line -->
