# syntax=docker/dockerfile:1
# ===========================================================================
# Image web KORA : build du frontend Vite puis service statique via nginx,
# qui fait aussi reverse-proxy des routes API/statiques vers le backend.
# Contexte de build = racine du dépôt.
# ===========================================================================

FROM node:20-bookworm-slim AS build
WORKDIR /app
ENV npm_config_audit=false npm_config_fund=false \
    npm_config_maxsockets=3 npm_config_fetch_retries=5 \
    npm_config_fetch_retry_mintimeout=20000 npm_config_fetch_retry_maxtimeout=120000
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
