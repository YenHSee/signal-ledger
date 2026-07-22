CREATE TABLE IF NOT EXISTS company_overview (
    symbol VARCHAR(10) PRIMARY KEY,
    asset_type VARCHAR(50),
    name VARCHAR(255),
    description TEXT,
    cik VARCHAR(20),
    exchange VARCHAR(50),
    currency VARCHAR(10),
    country VARCHAR(50),
    sector VARCHAR(100),
    industry VARCHAR(100),
    address TEXT,
    official_site TEXT,
    fiscal_year_end VARCHAR(20),
    latest_quarter DATE,
    market_capitalization BIGINT,
    ebitda BIGINT,
    pe_ratio NUMERIC(10, 4),
    peg_ratio NUMERIC(10, 4),
    book_value NUMERIC(10, 4),
    dividend_per_share NUMERIC(10, 4),
    dividend_yield NUMERIC(10, 4),
    eps NUMERIC(10, 4),
    revenue_per_share_ttm NUMERIC(10, 4),
    profit_margin NUMERIC(10, 4),
    operating_margin_ttm NUMERIC(10, 4),
    return_on_assets_ttm NUMERIC(10, 4),
    return_on_equity_ttm NUMERIC(10, 4),
    revenue_ttm BIGINT,
    gross_profit_ttm BIGINT,
    diluted_eps_ttm NUMERIC(10, 4),
    quarterly_earnings_growth_yoy NUMERIC(10, 4),
    quarterly_revenue_growth_yoy NUMERIC(10, 4),
    analyst_target_price NUMERIC(10, 4),
    analyst_rating_strong_buy INTEGER,
    analyst_rating_buy INTEGER,
    analyst_rating_hold INTEGER,
    analyst_rating_sell INTEGER,
    analyst_rating_strong_sell INTEGER,
    trailing_pe NUMERIC(10, 4),
    forward_pe NUMERIC(10, 4),
    price_to_sales_ratio_ttm NUMERIC(10, 4),
    price_to_book_ratio NUMERIC(10, 4),
    ev_to_revenue NUMERIC(10, 4),
    ev_to_ebitda NUMERIC(10, 4),
    beta NUMERIC(10, 4),
    week_52_high NUMERIC(10, 4),
    week_52_low NUMERIC(10, 4),
    day_50_moving_average NUMERIC(10, 4),
    day_200_moving_average NUMERIC(10, 4),
    shares_outstanding BIGINT,
    shares_float BIGINT,
    percent_insiders NUMERIC(10, 4),
    percent_institutions NUMERIC(10, 4),
    dividend_date DATE,
    ex_dividend_date DATE,
    is_sp500 BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    current_price NUMERIC(10, 4),
    price_as_of TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS daily_prices (
    symbol VARCHAR(10) REFERENCES company_overview(symbol),
    trade_date DATE,
    open_price NUMERIC(10, 4),
    high_price NUMERIC(10, 4),
    low_price NUMERIC(10, 4),
    close_price NUMERIC(10, 4),
    adjusted_close NUMERIC(10, 4),
    volume BIGINT,
    PRIMARY KEY (symbol, trade_date)
);

CREATE TABLE IF NOT EXISTS stock_news (
    id BIGSERIAL PRIMARY KEY,
    finnhub_id BIGINT NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    datetime BIGINT NOT NULL,
    headline TEXT NOT NULL,
    summary TEXT,
    source VARCHAR(100),
    url TEXT,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE stock_news
    DROP CONSTRAINT IF EXISTS stock_news_finnhub_id_key;

CREATE UNIQUE INDEX IF NOT EXISTS uq_sample_stock_news_fixture
    ON stock_news (finnhub_id, symbol);

CREATE INDEX IF NOT EXISTS idx_stock_news_symbol_date
    ON stock_news (symbol, trade_date);

CREATE TABLE IF NOT EXISTS sec_financial_snapshots (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    accession_number VARCHAR(32) NOT NULL,
    form VARCHAR(10) NOT NULL CHECK (form IN ('10-K', '10-Q')),
    filed_at DATE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    period_end DATE,
    primary_document TEXT,
    cik VARCHAR(10),
    entity_name TEXT,
    facts JSONB NOT NULL,
    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (symbol, accession_number)
);

CREATE INDEX IF NOT EXISTS idx_sec_financial_snapshots_symbol_filed
    ON sec_financial_snapshots (symbol, filed_at DESC);

CREATE TABLE IF NOT EXISTS investment_reports (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    model_tier VARCHAR(10),
    conclusion VARCHAR(20) NOT NULL,
    conviction_level VARCHAR(20),
    target_price NUMERIC(10, 2),
    upside_downside_pct VARCHAR(20),
    risk_level VARCHAR(20),
    reasoning TEXT,
    full_report TEXT,
    raw_financial_data JSONB,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE investment_reports
    ADD COLUMN IF NOT EXISTS report_schema_version INTEGER,
    ADD COLUMN IF NOT EXISTS analysis_as_of TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS generation_mode VARCHAR(50),
    ADD COLUMN IF NOT EXISTS model_provider VARCHAR(50),
    ADD COLUMN IF NOT EXISTS model_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS prompt_version VARCHAR(100),
    ADD COLUMN IF NOT EXISTS agent_outputs JSONB,
    ADD COLUMN IF NOT EXISTS generation_metadata JSONB;

DROP INDEX IF EXISTS uq_sample_investment_reports_fixture;

CREATE UNIQUE INDEX IF NOT EXISTS uq_sample_investment_reports_fixture_v2
    ON investment_reports (
        ticker, analysis_as_of, model_provider, model_name, prompt_version
    );

CREATE TABLE IF NOT EXISTS sample_dataset_metadata (
    singleton_id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (singleton_id = 1),
    schema_version INTEGER NOT NULL,
    dataset_version TEXT NOT NULL,
    dataset_status TEXT NOT NULL CHECK (dataset_status IN ('draft', 'ready')),
    data_as_of DATE,
    ticker_count INTEGER NOT NULL CHECK (ticker_count >= 0),
    seeded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
