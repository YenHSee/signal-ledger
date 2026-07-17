# data-python

Daily ETL, news ingestion, and LLM investment report generation for SignalLedger.

See the [root README](../../README.md) for the full project overview.

## Environment variables

Create a `.env` file in this directory:

```bash
cp .env.example .env
```

| Variable | Required | Description |
| --- | --- | --- |
| `DB_PASSWORD` | Yes | PostgreSQL password |
| `DB_HOST` | No | Default `127.0.0.1` |
| `DB_PORT` | No | Default `5432` — use **`5433`** when using root `docker compose` |
| `DB_USER` | No | Default `postgres` |
| `DB_NAME` | No | Default `signal_ledger` |
| `CF_NAMESPACE_ID` | Yes | Cloudflare KV namespace (Yahoo fundamentals cache) |
| `CF_API_TOKEN` | Yes | Cloudflare API token |
| `CF_ACCOUNT_ID` | No | Cloudflare account ID |
| `FINNHUB_API_KEY` | No | [Finnhub](https://finnhub.io) free key — news step skipped if unset |
| `OPENAI_API_KEY` | No | For GPT-4o report generation |
| `DEEPSEEK_API_KEY` | No | For DeepSeek report generation |
| `MODEL_PROVIDER` | No | Default `ollama` |
| `ALPHA_VANTAGE_API_KEY` | No | Legacy; not used by the daily ETL |

## Setup

```bash
pip install -r requirements.txt
```

## Scripts

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
(fundamentals, prices, and last-7-day news as "recent catalysts"). Reports are
saved as local JSON under `reports/` and inserted into `investment_reports`.

```bash
python main.py --tickers AAPL NVDA --tier normal
```

| `--tier` | Model | Report file suffix |
| --- | --- | --- |
| `smart` | GPT-4o (needs `OPENAI_API_KEY`) | `S` |
| `normal` (default) | DeepSeek (needs `DEEPSEEK_API_KEY`) | `N` |
| `local` | Ollama (`qwen2.5:7b`, free) | `L` |

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
- `investment_reports` — AI report history
