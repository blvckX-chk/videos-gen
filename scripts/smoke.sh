#!/usr/bin/env bash
# Smoke test KORA — vérifie que les endpoints clés répondent.
# Usage : ./scripts/smoke.sh [base_url]   (défaut : http://localhost:8000)
set -u

BASE="${1:-http://localhost:8000}"
SECRET="${ADMIN_SECRET:-}"
fail=0

check() {
  local path="$1" expect="${2:-200}"
  local code
  code="$(curl -s -o /dev/null -w '%{http_code}' "$BASE$path")"
  if [ "$code" = "$expect" ]; then
    printf '  OK   %-28s %s\n' "$path" "$code"
  else
    printf '  FAIL %-28s %s (attendu %s)\n' "$path" "$code" "$expect"
    fail=1
  fi
}

echo "KORA smoke test → $BASE"
check /health
check /api/providers
check /api/jobs
check /api/documents
check /api/identity/me
check /api/identity/chartes
check /api/design/info
check /api/campaign/jobs
check /api/copy/platforms

# Auth : si un secret est fourni, vérifier la bascule de rôle.
if [ -n "$SECRET" ]; then
  role_anon="$(curl -s "$BASE/api/identity/me" | grep -o '"role":"[a-z]*"' | head -1)"
  role_admin="$(curl -s -H "X-Admin-Secret: $SECRET" "$BASE/api/identity/me" | grep -o '"role":"[a-z]*"' | head -1)"
  echo "  auth  sans secret: $role_anon | avec secret: $role_admin"
  [ "$role_admin" = '"role":"admin"' ] || { echo "  FAIL bascule admin"; fail=1; }
fi

[ "$fail" = 0 ] && echo "=== SMOKE OK ===" || echo "=== SMOKE: ÉCHECS ==="
exit $fail
