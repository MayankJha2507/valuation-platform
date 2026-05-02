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

<!-- Add new entries above this line -->
