#!/usr/bin/env bash
# Batteria live di domande sul Wiki in produzione CED.
# Uso:
#   ./scripts/wiki-live-battery-ced.sh
# Variabili opzionali:
#   API_BASE=http://gaia.lan/api
#   ENV_FILE=.env.production
set -Eeuo pipefail

API_BASE="${API_BASE:-http://gaia.lan/api}"
ENV_FILE="${ENV_FILE:-.env.production}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Errore: env non trovato: $ENV_FILE" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "Errore: jq non disponibile." >&2
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

echo "==> Login $API_BASE/auth/login"
TOKEN="$(
  curl -fsS -X POST "$API_BASE/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}" \
  | jq -r '.access_token'
)"

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  echo "Errore: login fallito." >&2
  exit 1
fi

run_case() {
  local label="$1"
  local question="$2"
  local page_path="$3"
  local module_key="$4"

  local payload response status body answer mode detail
  payload="$(
    jq -nc \
      --arg question "$question" \
      --arg page_path "$page_path" \
      --arg module_key "$module_key" \
      '{
        question: $question,
        page_path: $page_path,
        module_key: (if $module_key == "" then null else $module_key end)
      }'
  )"

  response="$(
    curl -sS \
      -w $'\n%{http_code}' \
      -X POST "$API_BASE/wiki/chat" \
      -H "Authorization: Bearer $TOKEN" \
      -H 'Content-Type: application/json' \
      -d "$payload"
  )"

  status="$(printf '%s' "$response" | tail -n1)"
  body="$(printf '%s' "$response" | sed '$d')"
  answer="$(printf '%s' "$body" | jq -r '.answer // empty' 2>/dev/null || true)"
  mode="$(printf '%s' "$body" | jq -r '.mode // empty' 2>/dev/null || true)"
  detail="$(printf '%s' "$body" | jq -r '.detail // empty' 2>/dev/null || true)"

  echo ""
  echo "[$label]"
  echo "Q: $question"
  echo "Page: $page_path  Module: ${module_key:-<none>}"
  echo "HTTP: $status  Mode: ${mode:-<none>}"

  if [[ -n "$detail" ]]; then
    echo "Detail: $detail"
  fi

  if [[ -n "$answer" ]]; then
    printf 'Answer: %s\n' "$answer"
  else
    echo "Answer: <vuota>"
  fi
}

echo "==> Batteria live wiki su $API_BASE"

run_case "GIS root" "dove trovo il gis?" "/" ""
run_case "GIS root upper" "DOVE TROVO IL GIS?" "/" ""
run_case "Banca ore" "dove trovo la banca ore?" "/inaz" "inaz"
run_case "Contatori irrigui" "dove vedo i contatori irrigui?" "/catasto" "catasto"
run_case "Organigramma" "dove trovo l'organigramma?" "/" ""
run_case "Supporto wiki" "come apro il supporto wiki?" "/" ""
run_case "GIS page help" "cosa posso fare in questa pagina?" "/catasto/gis" "catasto"
run_case "GIS page intro" "come funziona questa pagina?" "/catasto/gis" "catasto"
run_case "Rete devices" "dove vedo i dispositivi di rete?" "/network" "rete"
run_case "Profilo" "dove trovo il profilo?" "/" ""
