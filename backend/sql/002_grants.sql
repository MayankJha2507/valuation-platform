-- Valuation Platform — Migration 002: grant table privileges
--
-- Supabase has two gates between the API and your data:
--   1. GRANT  — can this role touch the table at all?
--   2. RLS    — which rows can it see?
--
-- 001 set up RLS policies but assumed default GRANTs. Newer Supabase projects
-- don't auto-grant on new public-schema tables, so we make it explicit here.
--
-- Run this in Supabase: SQL Editor → New query → paste → Run.
-- Idempotent: GRANT is naturally re-runnable.

-- service_role: full DML access. Bypasses RLS. Used by the backend.
GRANT ALL ON TABLE public.stocks         TO service_role;
GRANT ALL ON TABLE public.price_history  TO service_role;
GRANT ALL ON TABLE public.financials     TO service_role;
GRANT ALL ON TABLE public.valuations     TO service_role;

-- anon (frontend) and authenticated: SELECT only. RLS policies still apply
-- on top of this and gate exactly which rows are returned.
GRANT SELECT ON TABLE public.stocks         TO anon, authenticated;
GRANT SELECT ON TABLE public.price_history  TO anon, authenticated;
GRANT SELECT ON TABLE public.financials     TO anon, authenticated;
GRANT SELECT ON TABLE public.valuations     TO anon, authenticated;

-- BIGSERIAL primary keys need sequence access for INSERTs.
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;
