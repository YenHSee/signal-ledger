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
