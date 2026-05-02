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

<!-- Add new entries above this line -->
