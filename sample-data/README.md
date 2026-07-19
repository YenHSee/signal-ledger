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

The committed `v1` draft currently contains fundamentals and one year of daily
prices for each of the ten tickers, covering 2025-07-18 through 2026-07-17.
News, reports, and redistribution review are still incomplete.

## Frozen report acceptance

Reports are accepted only when their timestamp falls inside the frozen price
range, their snapshot price matches a close from the preceding seven days, and
their stated upside or downside can be reproduced from the snapshot and target
prices. The loader also requires the full report sections used by the UI,
rejects a conflicting embedded generation date, and rejects catalysts that are
not present in `stock_news.json`.

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

## Seed the draft locally

With PostgreSQL available on host port `5433`:

```bash
cd packages/data-python
APP_MODE=sample \
DB_NAME=signal_ledger_sample \
DB_PORT=5433 \
DB_PASSWORD=password123 \
python scripts/seed_sample_data.py --allow-draft
```

Running the command again is idempotent. The final Docker demo will call the same
seeder without `--allow-draft`, so an unfinished dataset cannot be published.
