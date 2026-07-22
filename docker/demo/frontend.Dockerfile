FROM node:22.18.0-alpine AS build

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages/api-types/package.json packages/api-types/package.json
COPY packages/backend-node/package.json packages/backend-node/package.json
COPY packages/frontend-web/package.json packages/frontend-web/package.json
RUN pnpm install --frozen-lockfile --filter frontend-web...

COPY packages/api-types packages/api-types
COPY packages/frontend-web packages/frontend-web

ARG VITE_API_BASE=/api
ENV VITE_API_BASE=$VITE_API_BASE
RUN pnpm --filter frontend-web build

FROM nginx:1.27-alpine AS runtime

COPY docker/demo/nginx.conf /etc/nginx/conf.d/default.conf
COPY --chmod=755 docker/demo/print-demo-url.sh /docker-entrypoint.d/40-signal-ledger-url.sh
COPY --from=build /app/packages/frontend-web/dist /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=5s --timeout=3s --retries=20 \
  CMD wget -q -O /dev/null http://127.0.0.1/healthz || exit 1
