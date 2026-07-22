-- Additive migration: legacy rows intentionally remain NULL for all new fields.
ALTER TABLE investment_reports
    ADD COLUMN IF NOT EXISTS report_schema_version INTEGER,
    ADD COLUMN IF NOT EXISTS analysis_as_of TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS generation_mode VARCHAR(50),
    ADD COLUMN IF NOT EXISTS model_provider VARCHAR(50),
    ADD COLUMN IF NOT EXISTS model_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS prompt_version VARCHAR(100),
    ADD COLUMN IF NOT EXISTS agent_outputs JSONB,
    ADD COLUMN IF NOT EXISTS generation_metadata JSONB;

CREATE INDEX IF NOT EXISTS idx_investment_reports_analysis_as_of
    ON investment_reports (ticker, analysis_as_of DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_investment_reports_auditable_run
    ON investment_reports (
        ticker, analysis_as_of, model_provider, model_name, prompt_version
    )
    WHERE analysis_as_of IS NOT NULL;
