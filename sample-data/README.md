# Sample data

This directory contains versioned, frozen fixtures for SignalLedger sample mode.
It is part of the application source and must never contain credentials or data
that is not safe to redistribute.

## Dataset lifecycle

Each version has a `manifest.json` and four JSON arrays:

- `company_overview.json`
- `daily_prices.json`
- `stock_news.json`
- `investment_reports.json`

A new dataset starts with `status: "draft"`. The seeder rejects draft datasets
unless a developer explicitly passes `--allow-draft`. Change the status to
`ready` only after row counts, date coverage, redistribution safety, and all ten
ticker pages have been verified.

The committed `v1` draft currently contains fundamentals and 2026 year-to-date
daily prices for each of the ten tickers, covering the first trading day on
2026-01-02 through 2026-07-17. It also contains 200 curated 2026 YTD news items
and 50 schema-v2 historical reports (five per ticker). Redistribution review is
still incomplete, so the dataset remains a draft.

`report_inputs/<TICKER>.json` is a non-seeded generation input. It contains
the longer price history needed for 50/200-day calculations plus point-in-time
SEC 10-K/10-Q facts and filing metadata. At each report date the builder selects
only filings already public on that date. The browser-facing
sample database still receives only the compact YTD tables above.

## Known data limitations

The sample does not reconstruct historical analyst-consensus datasets. In the
point-in-time report snapshots, `forward_pe`, `peg_ratio`,
`analyst_target_price`, and `percent_institutions` remain `null` when no free,
redistributable historical source is available. The frontend renders these
values as `—`; the report generator must not infer or fabricate them.

When sufficient SEC data exists, `trailing_pe` is derived from the frozen price
and the latest already-filed annual diluted EPS. Its snapshot metadata and the
report Data Limitations section identify that basis; it is not a reconstructed
TTM or a forward estimate. Point-in-time balance-sheet and cash-flow values come
from SEC 10-K/10-Q filings that were public by the analysis date.

The compact seeded price table begins on 2026-01-02. Non-seeded
`report_inputs/<TICKER>.json` contains the earlier prices required to calculate
50-day and 200-day moving averages without expanding the browser-facing chart.
The frozen reports are illustrative AI research, not current analysis or
financial advice.

## Frozen report acceptance

Schema-v2 reports are accepted only when `analysis_as_of` falls inside the frozen price
range, their snapshot price matches a close from the preceding seven days, and
their stated upside or downside can be reproduced from the snapshot and target
prices. The loader also requires the full report sections used by the UI,
rejects a conflicting embedded analysis date, and rejects catalysts that are
not present in `stock_news.json`.

Every accepted report must have complete `agent_outputs` and
`generation_metadata`. The unique `final_run_id` must link the canonical
conclusion to its actual provider response model, prompt version, finish reason,
and token usage. Requested model names are never substituted for missing
response metadata. Legacy live reports remain readable as `legacy_incomplete`
but cannot enter the auditable frozen track record.

When no frozen news is available, the report must say so in its Data Limitations
section. Structurally complete live reports are not copied automatically: they
must pass these historical-consistency checks first.

## Safety boundary

The seeder only runs when both conditions are true:

```text
APP_MODE=sample
DB_NAME=signal_ledger_sample
```

It replaces rows only inside that dedicated sample database, in one transaction.
It never calls yfinance, Finnhub, an LLM, or any other external provider.

## Build the frozen fundamentals and prices

Only a maintainer with the live database and network access runs this command. It
opens the live database in a read-only transaction and writes fixtures atomically:

```bash
cd packages/data-python
APP_MODE=live \
DB_NAME=signal_ledger \
DB_PORT=5433 \
DB_PASSWORD=password123 \
.venv/bin/python scripts/export_sample_data.py
```

The exporter downloads prices while building the fixture; sample mode never does.

Freeze the longer price and SEC inputs for the ten sample tickers:

```bash
cd packages/data-python
SEC_USER_AGENT="SignalLedger/1.0 maintainer@example.com" \
.venv/bin/python scripts/export_report_inputs.py \
  --ticker AAPL --ticker MSFT --ticker NVDA --ticker GOOGL --ticker AMZN \
  --ticker META --ticker TSLA --ticker AMD --ticker JPM --ticker WMT \
  --earliest-as-of 2026-01-09 --as-of 2026-07-17
```

Validate all 50 point-in-time snapshots without an LLM call:

```bash
APP_MODE=live DB_NAME=signal_ledger \
.venv/bin/python scripts/build_sample_reports.py --validate-schedule
```

Before a full paid backfill, generate and validate one isolated pilot:

```bash
APP_MODE=live DB_NAME=signal_ledger \
.venv/bin/python scripts/build_sample_reports.py \
  --pilot-ticker NVDA --pilot-date 2026-01-09 \
  --pilot-output reports/2026-01-09_NVDA_N_pilot.json --tier normal
```

After approving the pilot, the resumable full DeepSeek backfill is:

```bash
APP_MODE=live DB_NAME=signal_ledger \
.venv/bin/python scripts/build_sample_reports.py --tier normal
```

The schedule contains five reports for every sample ticker on 2026-01-09,
2026-02-20, 2026-03-31, 2026-05-15, and 2026-07-17. Individual report archives
under `packages/data-python/reports/` remain local and ignored; the validated
50-report fixture in `v1/investment_reports.json` is what the sample seeder
loads.

## Seed the draft locally

The normal local demo path builds the seeder, API, and frontend with no external
keys or per-process environment variables:

```bash
docker compose --profile demo up --build
```

Open <http://127.0.0.1:8080/stock/screener>. The isolated sample database is
also exposed on host port `5434` for local inspection. Its database name is
`signal_ledger_sample`.

For seeder development without the full Docker demo, use the manual command
below.

With PostgreSQL available on host port `5433`:

```bash
cd packages/data-python
APP_MODE=sample \
DB_NAME=signal_ledger_sample \
DB_PORT=5433 \
DB_PASSWORD=password123 \
python scripts/seed_sample_data.py --allow-draft
```

Running the command again is idempotent. The local demo currently passes
`--allow-draft` and displays its draft metadata. Remove that flag and change the
fixture status to `ready` only after redistribution review is approved.
