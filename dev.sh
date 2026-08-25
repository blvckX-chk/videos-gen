#!/usr/bin/env bash
# Lance backend (FastAPI) + frontend (Vite) en parallèle pour le développement.
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# --- Backend ---
cd "$ROOT/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
fi
[ -f .env ] || cp .env.example .env
./.venv/bin/uvicorn app.main:app --reload --port 8000 &
BACK=$!

# --- Remotion (assure que node_modules est prêt, pas de serveur) ---
if [ -d "$ROOT/remotion" ]; then
  cd "$ROOT/remotion"
  [ -d node_modules ] || npm install --no-audit --no-fund
fi

# --- Frontend ---
cd "$ROOT/frontend"
[ -d node_modules ] || npm install
npm run dev &
FRONT=$!

trap "kill $BACK $FRONT 2>/dev/null" EXIT
echo "Backend : http://localhost:8000  (docs: /docs)"
echo "Frontend: http://localhost:5173"
wait
