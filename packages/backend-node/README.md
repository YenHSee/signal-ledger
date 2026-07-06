# backend-node

Read-only NestJS REST API for the Stock Analyst frontend. Queries PostgreSQL
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
