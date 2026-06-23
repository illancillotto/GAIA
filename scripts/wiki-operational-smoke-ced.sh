#!/usr/bin/env bash
# Smoke test Wiki operativo su server CED (post-deploy).
# Uso remoto: ssh serverCed 'bash -s' < scripts/wiki-operational-smoke-ced.sh
# Uso locale sul server: GAIA_DIR=/opt/gaia ./scripts/wiki-operational-smoke-ced.sh
set -Eeuo pipefail

GAIA_DIR="${GAIA_DIR:-/opt/gaia}"
API_BASE="${API_BASE:-http://127.0.0.1:8080/api}"
ENV_FILE="${ENV_FILE:-$GAIA_DIR/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Errore: env non trovato: $ENV_FILE" >&2
  exit 1
fi

read_env() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" | tail -n1 | cut -d= -f2-
}

ADMIN_USER="$(read_env BOOTSTRAP_ADMIN_USERNAME)"
ADMIN_PASS="$(read_env BOOTSTRAP_ADMIN_PASSWORD)"

if [[ -z "$ADMIN_USER" || -z "$ADMIN_PASS" ]]; then
  echo "Errore: BOOTSTRAP_ADMIN_USERNAME/PASSWORD mancanti in $ENV_FILE" >&2
  exit 1
fi

echo "==> Login API $API_BASE"
TOKEN="$(
  curl -fsS -X POST "$API_BASE/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"

wiki_chat() {
  local payload="$1"
  curl -fsS -X POST "$API_BASE/wiki/chat" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -d "$payload"
}

check_answer() {
  local label="$1"
  local answer="$2"
  shift 2
  local fail=0
  local token

  for token in "$@"; do
    if [[ "$token" == !* ]]; then
      token="${token#!}"
      if echo "$answer" | grep -qi "$token"; then
        echo "  FAIL: trovato vietato '$token'"
        fail=1
      fi
    else
      if ! echo "$answer" | grep -qi "$token"; then
        echo "  FAIL: manca atteso '$token'"
        fail=1
      fi
    fi
  done

  if (( fail == 0 )); then
    echo "  OK"
  else
    echo "  Risposta: ${answer:0:400}..."
    return 1
  fi
}

FAILURES=0

run_case() {
  local label="$1"
  local payload="$2"
  shift 2
  echo ""
  echo "==> $label"
  local raw answer mode found
  if ! raw="$(wiki_chat "$payload")"; then
    echo "  FAIL: HTTP/API error"
    FAILURES=$((FAILURES + 1))
    return
  fi
  answer="$(printf '%s' "$raw" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("answer",""))')"
  mode="$(printf '%s' "$raw" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("mode",""))')"
  found="$(printf '%s' "$raw" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("found",""))')"
  echo "  mode=$mode found=$found"
  if ! check_answer "$label" "$answer" "$@"; then
    FAILURES=$((FAILURES + 1))
  fi
}

echo "==> Wiki operational smoke su $API_BASE"

run_case "Proprietario terreno (chiarimento)" \
  '{"question":"mi serve trovare un proprietario di un terreno cosa devo fare?","module_key":"catasto","page_path":"/catasto/particelle"}' \
  comune foglio particella '!workspace' '!documento fornito'

run_case "Overview modulo catasto" \
  '{"question":"come funziona il modulo catasto?","module_key":"wiki","page_path":"/wiki"}' \
  catasto Scopo '!workspace'

run_case "Page intro widget" \
  '{"question":"cosa posso fare qui?","module_key":"catasto","page_path":"/catasto/letture-contatori"}' \
  contator Scopo '!workspace'

run_case "Lettura contatori" \
  '{"question":"come vedo una lettura di contatori?","module_key":"catasto","page_path":"/catasto/letture-contatori"}' \
  contator '!workspace' '!documento fornito'

run_case "Supporto Wiki navigazione" \
  '{"question":"dove trovo le richieste supporto wiki?","module_key":"wiki","page_path":"/wiki"}' \
  '/wiki/support' '!workspace'

echo ""
if (( FAILURES > 0 )); then
  echo "Smoke Wiki: $FAILURES casi falliti"
  exit 1
fi
echo "Smoke Wiki: tutti i casi passati"
