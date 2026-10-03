# syntax=docker/dockerfile:1
# ===========================================================================
# Image backend KORA : FastAPI + Remotion (Node) + Chromium headless + FFmpeg.
# Contexte de build = racine du dépôt (a besoin de backend/ ET remotion/).
# ===========================================================================

# --------------------------------------------------------------------------- #
# Stage 1 — dépendances Node de Remotion (couche mise en cache)
# --------------------------------------------------------------------------- #
FROM node:20-bookworm-slim AS remotion
WORKDIR /app/remotion
ENV npm_config_audit=false npm_config_fund=false \
    npm_config_maxsockets=3 npm_config_fetch_retries=5 \
    npm_config_fetch_retry_mintimeout=20000 npm_config_fetch_retry_maxtimeout=120000
COPY remotion/package.json remotion/package-lock.json ./
RUN npm ci || npm install
COPY remotion/ ./

# --------------------------------------------------------------------------- #
# Stage 2 — runtime (Python + Node + Chromium + FFmpeg)
# --------------------------------------------------------------------------- #
FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    REMOTION_CHROMIUM=/opt/chromium/headless_shell \
    NODE_ENV=production

# Node 20 (pour `npx remotion`), ffmpeg, libsndfile (soundfile), polices.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl gnupg ffmpeg libsndfile1 \
      fonts-dejavu-core fonts-liberation \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dépendances Python + Playwright (sert uniquement à fournir chrome-headless-shell,
# le binaire que Remotion sait piloter).
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt "playwright==1.47.0"

# Chromium headless-shell + libs système, puis symlink à chemin stable.
RUN playwright install --with-deps chromium \
 && mkdir -p /opt/chromium \
 && ln -sf "$(find /opt/pw-browsers -type f \( -name headless_shell -o -name chrome-headless-shell \) | head -n1)" \
           /opt/chromium/headless_shell \
 && test -x /opt/chromium/headless_shell \
 && chmod -R a+rX /opt/pw-browsers /opt/chromium

# Remotion (node_modules + source) depuis le stage Node.
COPY --from=remotion /app/remotion /app/remotion

# Code backend.
COPY backend /app/backend

# Utilisateur non-root + dossier de persistance (monté en volume).
RUN useradd -m -u 10001 kora \
 && mkdir -p /app/storage \
 && chown -R kora:kora /app/storage /app/remotion
USER kora

WORKDIR /app/backend
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').getcode()==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
