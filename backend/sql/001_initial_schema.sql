-- Valuation Platform — Initial schema
--
-- Run this in Supabase: SQL Editor → New query → paste → Run.
-- Idempotent: safe to re-run (uses IF NOT EXISTS / DROP IF EXISTS where relevant).

-- =========================================
-- Helper: auto-update `updated_at` on row UPDATE
-- =========================================
CREATE OR REPLACE FUNCTION public.trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================================
-- Table 1: stocks  (Nifty 50 master list)
-- =========================================
CREATE TABLE IF NOT EXISTS public.stocks (
  id              BIGSERIAL PRIMARY KEY,
  ticker          TEXT NOT NULL UNIQUE,            -- e.g. RELIANCE.NS
  nse_symbol      TEXT NOT NULL UNIQUE,            -- e.g. RELIANCE
  company_name    TEXT NOT NULL,
  sector          TEXT,
  industry        TEXT,
  isin            TEXT UNIQUE,
  market_cap_inr  NUMERIC,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS set_updated_at ON public.stocks;
CREATE TRIGGER set_updated_at
  BEFORE UPDATE ON public.stocks
  FOR EACH ROW EXECUTE FUNCTION public.trigger_set_updated_at();

ALTER TABLE public.stocks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "stocks_anon_select" ON public.stocks;
CREATE POLICY "stocks_anon_select" ON public.stocks
  FOR SELECT TO anon USING (true);

-- =========================================
-- Table 2: price_history  (daily OHLCV)
-- =========================================
CREATE TABLE IF NOT EXISTS public.price_history (
  id          BIGSERIAL PRIMARY KEY,
  stock_id    BIGINT NOT NULL REFERENCES public.stocks(id) ON DELETE CASCADE,
  date        DATE NOT NULL,
  open        NUMERIC(20, 4),
  high        NUMERIC(20, 4),
  low         NUMERIC(20, 4),
  close       NUMERIC(20, 4),
  adj_close   NUMERIC(20, 4),
  volume      BIGINT,
  CONSTRAINT price_history_stock_date_unique UNIQUE (stock_id, date)
);

ALTER TABLE public.price_history ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "price_history_anon_select" ON public.price_history;
CREATE POLICY "price_history_anon_select" ON public.price_history
  FOR SELECT TO anon USING (true);

-- =========================================
-- Table 3: financials  (quarterly + annual)
-- =========================================
CREATE TABLE IF NOT EXISTS public.financials (
  id                    BIGSERIAL PRIMARY KEY,
  stock_id              BIGINT NOT NULL REFERENCES public.stocks(id) ON DELETE CASCADE,
  period_type           TEXT NOT NULL CHECK (period_type IN ('quarterly', 'annual')),
  period_end_date       DATE NOT NULL,
  fiscal_year           INT NOT NULL,
  fiscal_quarter        INT CHECK (fiscal_quarter BETWEEN 1 AND 4),

  -- Income statement
  revenue               NUMERIC,
  gross_profit          NUMERIC,
  operating_income      NUMERIC,
  net_income            NUMERIC,
  eps                   NUMERIC,

  -- Balance sheet
  total_assets          NUMERIC,
  total_liabilities     NUMERIC,
  total_equity          NUMERIC,
  cash_and_equivalents  NUMERIC,
  total_debt            NUMERIC,
  shares_outstanding    NUMERIC,

  -- Cash flow
  operating_cash_flow   NUMERIC,
  capital_expenditure   NUMERIC,
  free_cash_flow        NUMERIC,

  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT financials_stock_period_unique UNIQUE (stock_id, period_type, period_end_date)
);

DROP TRIGGER IF EXISTS set_updated_at ON public.financials;
CREATE TRIGGER set_updated_at
  BEFORE UPDATE ON public.financials
  FOR EACH ROW EXECUTE FUNCTION public.trigger_set_updated_at();

ALTER TABLE public.financials ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "financials_anon_select" ON public.financials;
CREATE POLICY "financials_anon_select" ON public.financials
  FOR SELECT TO anon USING (true);

-- =========================================
-- Table 4: valuations  (computed snapshots)
-- =========================================
CREATE TABLE IF NOT EXISTS public.valuations (
  id                      BIGSERIAL PRIMARY KEY,
  stock_id                BIGINT NOT NULL REFERENCES public.stocks(id) ON DELETE CASCADE,
  as_of_date              DATE NOT NULL,
  current_price           NUMERIC(20, 4),
  intrinsic_value_dcf     NUMERIC(20, 4),

  -- Ratios for this stock at as_of_date
  pe_ratio                NUMERIC,
  pb_ratio                NUMERIC,
  ev_ebitda               NUMERIC,
  ps_ratio                NUMERIC,
  peg_ratio               NUMERIC,

  -- Sector means at as_of_date
  pe_sector_avg           NUMERIC,
  pb_sector_avg           NUMERIC,
  ev_ebitda_sector_avg    NUMERIC,
  ps_sector_avg           NUMERIC,
  peg_sector_avg          NUMERIC,

  -- This stock's own 5-year means
  pe_5y_avg               NUMERIC,
  pb_5y_avg               NUMERIC,
  ev_ebitda_5y_avg        NUMERIC,
  ps_5y_avg               NUMERIC,
  peg_5y_avg              NUMERIC,

  verdict                 TEXT CHECK (verdict IN ('undervalued', 'fairly_valued', 'overvalued')),
  verdict_explanation     TEXT,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT valuations_stock_date_unique UNIQUE (stock_id, as_of_date)
);

ALTER TABLE public.valuations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "valuations_anon_select" ON public.valuations;
CREATE POLICY "valuations_anon_select" ON public.valuations
  FOR SELECT TO anon USING (true);
