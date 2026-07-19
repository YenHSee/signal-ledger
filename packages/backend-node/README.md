# backend-node

Read-only NestJS REST API for the SignalLedger frontend. Queries PostgreSQL
(prices, fundamentals, screener, investment reports, news) — no external
data fetching at request time.

See the [root README](../../README.md) for the full project overview.

## Run locally

```bash
pnpm install   # from repo root
pnpm start:dev # http://localhost:4000/api
```

Requires PostgreSQL with data populated by `packages/data-python` ETL.
API prefix: `/api`.

## Runtime mode

Set `APP_MODE` explicitly in each deployment:

- `live` (default) reads the normal database and rejects database names ending
  in `_sample`.
- `sample` is reserved for frozen demo data and must use the exact database name
  `signal_ledger_sample`.

The API is read-only in both modes. `GET /api/meta` reports the active mode and
sample dataset metadata; `GET /api/health` verifies the database connection.
Startup fails immediately when the mode or database boundary is invalid.
