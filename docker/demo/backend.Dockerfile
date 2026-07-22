FROM node:22.18.0-alpine AS build

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages/api-types/package.json packages/api-types/package.json
COPY packages/backend-node/package.json packages/backend-node/package.json
COPY packages/frontend-web/package.json packages/frontend-web/package.json
RUN pnpm install --frozen-lockfile --filter backend-node...

COPY packages/api-types packages/api-types
COPY packages/backend-node packages/backend-node
RUN pnpm --filter backend-node build
RUN pnpm --filter backend-node deploy --prod /prod/backend

FROM node:22.18.0-alpine AS runtime

ENV NODE_ENV=production
WORKDIR /app

COPY --from=build /prod/backend ./
COPY --from=build /app/packages/backend-node/dist ./dist

EXPOSE 4000
CMD ["node", "dist/main.js"]
