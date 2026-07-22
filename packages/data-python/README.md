# data-python

Daily ETL, news ingestion, and LLM investment report generation for SignalLedger.

See the [root README](../../README.md) for the full project overview.

## Environment variables

Create a `.env` file in this directory:

```bash
cp .env.example .env
```

| Variable                | Required | Description                                                         |
| ----------------------- | -------- | ------------------------------------------------------------------- |
| `APP_MODE`              | No       | Default `live`; all ETL/report writes require `live`                |
| `DB_PASSWORD`           | Yes      | PostgreSQL password                                                 |
| `DB_HOST`               | No       | Default `127.0.0.1`                                                 |
| `DB_PORT`               | No       | Default `5432` — use **`5433`** when using root `docker compose`    |
| `DB_USER`               | No       | Default `postgres`                                                  |
| `DB_NAME`               | No       | Default `signal_ledger`                                             |
| `CF_NAMESPACE_ID`       | Yes      | Cloudflare KV namespace (Yahoo fundamentals cache)                  |
| `CF_API_TOKEN`          | Yes      | Cloudflare API token                                                |
| `CF_ACCOUNT_ID`         | No       | Cloudflare account ID                                               |
| `FINNHUB_API_KEY`       | No       | [Finnhub](https://finnhub.io) free key — news step skipped if unset |
| `OPENAI_API_KEY`        | No       | For GPT-4o report generation                                        |
| `DEEPSEEK_API_KEY`      | No       | For DeepSeek report generation                                      |
| `MODEL_PROVIDER`        | No       | Default `ollama`                                                    |
| `ALPHA_VANTAGE_API_KEY` | No       | Legacy; not used by the daily ETL                                   |

## Runtime safety

This package owns live data writes. ETL, schema initialization, news backfill,
and report persistence stop before writing unless `APP_MODE=live`, and live
writes are rejected when `DB_NAME` ends in `_sample`. The sample seeder uses a separate guard requiring both `APP_MODE=sample` and the exact database
name `signal_ledger_sample`.

## Setup

```bash
pip install -r requirements.txt
```

## Scripts

### Frozen sample fundamentals and prices

Maintainers can rebuild the v1 draft fixture from a read-only live fundamentals
snapshot and a fixed yfinance price window:

```bash
APP_MODE=live DB_NAME=signal_ledger DB_PORT=5433 \
  python scripts/export_sample_data.py --dry-run
```

Remove `--dry-run` only after coverage validation succeeds. End users never run
this exporter; sample mode reads the committed frozen JSON.

### Daily ETL (prices, fundamentals, news)

```bash
python scripts/daily_etl_pipeline.py
```

Steps: init schema → truncate/reload `daily_prices` → sync S&P 500 fundamentals
(yfinance) → upsert company news (Finnhub, last 3 days; 30-day backfill on first run).

### News backfill (one-time or repair)

For hot tickers, Finnhub caps wide date-range responses (~250 items). This script
does a broad pull plus per-day fetches on anomaly days (±2% move or 2× volume)
so chart markers always have news behind them.

```bash
python scripts/backfill_news.py                         # full S&P 500, 30 days
python scripts/backfill_news.py --days 30 --tickers AAPL,MSFT
python scripts/backfill_news.py --skip-broad            # anomaly days only
python scripts/backfill_news.py --skip-anomaly          # broad pull only
```

### AI report generation

Generates institutional-style investment reports from data already in the DB
(fundamentals, prices, SEC snapshots, and relevant news from the preceding 30
days as "recent catalysts"). Reports are
saved as local JSON under `reports/` and inserted into `investment_reports`.

```bash
python main.py --tickers AAPL NVDA --tier normal
```

| `--tier`           | Model                               | Report file suffix |
| ------------------ | ----------------------------------- | ------------------ |
| `smart`            | GPT-4o (needs `OPENAI_API_KEY`)     | `S`                |
| `normal` (default) | DeepSeek (needs `DEEPSEEK_API_KEY`) | `N`                |
| `local`            | Ollama (`qwen2.5:7b`, free)         | `L`                |

Synchronize free SEC 10-K/10-Q balance-sheet and cash-flow snapshots before
generating live reports:

```bash
APP_MODE=live DB_NAME=signal_ledger \
.venv/bin/python scripts/sync_sec_financials.py --tickers AAPL NVDA TSLA
```

## Layout

- `main.py` — report-generation CLI entry point
- `scripts/` — daily ETL and news backfill
- `db/` — connection pool, schema, repositories, AI context builder
- `agents/` + `core/` — LangGraph analyst agent and LLM factory
- `tools/` — yfinance / Finnhub / Wikipedia fetchers
- `utils/` — data transformers (API payload → DB rows)

## Tables owned by this package

Python manages schema via `db/schema.py` → `init_tables()`:

- `company_overview` — fundamentals snapshot
- `daily_prices` — OHLCV (truncated and reloaded each ETL run)
- `stock_news` — news archive (append/upsert by `finnhub_id`)
- `sec_financial_snapshots` — accession-keyed SEC 10-K/10-Q facts
- `investment_reports` — AI report history
