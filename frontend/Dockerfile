FROM node:22-slim AS base
RUN corepack enable
WORKDIR /app
# Non-interactive: pnpm's dependency status check (introduced in newer pnpm
# releases) can decide node_modules needs purging/reinstalling before a run
# script, and refuses to do that without a TTY to confirm — which a Docker
# RUN step never has. CI=true is pnpm's own documented way to tell it this
# is an automated environment, not a case of "silently skip the check."
ENV CI=true

FROM base AS deps
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM base AS build
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN pnpm run build

FROM base AS runtime
ENV NODE_ENV=production
COPY --from=build /app/public ./public
COPY --from=build /app/.next ./.next
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json
EXPOSE 3000
CMD ["pnpm", "run", "start"]
