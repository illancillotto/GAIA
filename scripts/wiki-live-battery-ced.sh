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
REPORT_FORMAT="${REPORT_FORMAT:-text}"

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

TOTAL_CASES=0
FAILED_CASES=0
LAST_CASE_VERDICT=""
MODULE_NAMES=()
MODULE_TOTALS=()
MODULE_FAILURES=()

contains_ci() {
  local haystack="$1"
  local needle="$2"
  printf '%s' "$haystack" | grep -Fqi "$needle"
}

print_case_result() {
  local verdict="$1"
  local category="$2"
  local label="$3"
  local question="$4"
  local page_path="$5"
  local module_key="$6"
  local status="$7"
  local mode="$8"
  local detail="$9"
  local answer="${10}"

  if [[ "$REPORT_FORMAT" == "tsv" ]]; then
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$verdict" "$category" "$label" "$question" "$page_path" "${module_key:-<none>}" \
      "$status" "${mode:-<none>}" "${detail:-}" "${answer:-}"
    return
  fi

  echo ""
  echo "[$category] $label"
  echo "Verdict: $verdict"
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

find_module_index() {
  local module_name="$1"
  local i
  for i in "${!MODULE_NAMES[@]}"; do
    if [[ "${MODULE_NAMES[$i]}" == "$module_name" ]]; then
      printf '%s' "$i"
      return
    fi
  done
  printf '%s' "-1"
}

record_module_case() {
  local module_name="$1"
  local verdict="$2"
  local idx

  idx="$(find_module_index "$module_name")"
  if [[ "$idx" == "-1" ]]; then
    MODULE_NAMES+=("$module_name")
    MODULE_TOTALS+=(0)
    MODULE_FAILURES+=(0)
    idx=$((${#MODULE_NAMES[@]} - 1))
  fi

  MODULE_TOTALS[$idx]=$((MODULE_TOTALS[$idx] + 1))
  if [[ "$verdict" == "FAIL" ]]; then
    MODULE_FAILURES[$idx]=$((MODULE_FAILURES[$idx] + 1))
  fi
}

run_case() {
  local category="$1"
  local label="$2"
  local question="$3"
  local page_path="$4"
  local module_key="$5"
  local expect_status="$6"
  local expect_answer="$7"
  local forbid_answer="$8"

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

  TOTAL_CASES=$((TOTAL_CASES + 1))
  status="$(printf '%s' "$response" | tail -n1)"
  body="$(printf '%s' "$response" | sed '$d')"
  answer="$(printf '%s' "$body" | jq -r '.answer // empty' 2>/dev/null || true)"
  mode="$(printf '%s' "$body" | jq -r '.mode // empty' 2>/dev/null || true)"
  detail="$(printf '%s' "$body" | jq -r '.detail // empty' 2>/dev/null || true)"

  local verdict="PASS"
  if [[ "$status" != "$expect_status" ]]; then
    verdict="FAIL"
  fi
  if [[ "$verdict" == "PASS" && -n "$expect_answer" ]] && ! contains_ci "$answer" "$expect_answer"; then
    verdict="FAIL"
  fi
  if [[ "$verdict" == "PASS" && -n "$forbid_answer" ]] && contains_ci "$answer" "$forbid_answer"; then
    verdict="FAIL"
  fi
  if [[ "$verdict" == "FAIL" ]]; then
    FAILED_CASES=$((FAILED_CASES + 1))
  fi
  LAST_CASE_VERDICT="$verdict"

  print_case_result \
    "$verdict" "$category" "$label" "$question" "$page_path" "$module_key" \
    "$status" "$mode" "$detail" "$answer"
}

run_module_case() {
  local module_name="$1"
  local category="$2"
  local label="$3"
  local question="$4"
  local page_path="$5"
  local module_key="$6"
  local expect_status="$7"
  local expect_answer="$8"
  local forbid_answer="$9"

  run_case \
    "$category" "$label" "$question" "$page_path" "$module_key" \
    "$expect_status" "$expect_answer" "$forbid_answer"
  record_module_case "$module_name" "$LAST_CASE_VERDICT"
}

echo "==> Batteria live wiki su $API_BASE"

run_module_case "catasto" "catasto" "GIS root" "dove trovo il gis?" "/" "" "200" "/catasto/gis" "In questa pagina posso aiutarti"
run_module_case "catasto" "catasto" "Particelle" "dove trovo le particelle?" "/" "" "200" "/catasto/particelle" "In questa pagina posso aiutarti"
run_module_case "catasto" "catasto" "Contatori irrigui" "dove trovo i contatori irrigui?" "/" "" "200" "/catasto/letture-contatori" "In questa pagina posso aiutarti"
run_module_case "catasto" "catasto" "Pagina GIS" "cosa posso fare in questa pagina?" "/catasto/gis" "catasto" "200" "GIS Catasto" "non è indicata quale pagina stai guardando"
run_module_case "catasto" "catasto" "Proprietario terreno" "mi serve trovare un proprietario di un terreno cosa devo fare?" "/catasto/particelle" "catasto" "200" "foglio" "non riesce a sintetizzarli"

run_module_case "operazioni" "operazioni" "Pratiche" "dove trovo le pratiche?" "/" "" "200" "/operazioni/pratiche" "In questa pagina posso aiutarti"
run_module_case "operazioni" "operazioni" "Attivita" "dove trovo le attivita?" "/" "" "200" "/operazioni/attivita" "In questa pagina posso aiutarti"
run_module_case "operazioni" "operazioni" "Mezzi" "dove trovo i mezzi?" "/" "" "200" "/operazioni/mezzi" "In questa pagina posso aiutarti"
run_module_case "operazioni" "operazioni" "Analisi" "dove trovo le analisi operative?" "/" "" "200" "/operazioni/analisi" "In questa pagina posso aiutarti"

run_module_case "presenze" "presenze" "Banca ore" "dove trovo la banca ore?" "/" "" "200" "/inaz/banca-ore" "In questa pagina Inaz posso aiutarti"
run_module_case "presenze" "presenze" "Giornaliere" "dove trovo le giornaliere?" "/" "" "200" "/inaz/giornaliere" "In questa pagina Inaz posso aiutarti"
run_module_case "presenze" "presenze" "Collaboratori" "dove trovo i collaboratori?" "/" "" "200" "/inaz/collaboratori" "In questa pagina Inaz posso aiutarti"
run_module_case "presenze" "presenze" "Saldo banca ore" "come leggo saldo e liquidabile della banca ore?" "/inaz/banca-ore" "inaz" "200" "banca ore" "non riesce a sintetizzarli"

run_module_case "ruolo" "ruolo" "Avvisi" "dove trovo gli avvisi del ruolo?" "/" "" "200" "/ruolo/avvisi" "In questa pagina posso aiutarti"
run_module_case "ruolo" "ruolo" "Particelle ruolo" "dove trovo le particelle del ruolo?" "/" "" "200" "/ruolo/particelle" "In questa pagina posso aiutarti"
run_module_case "ruolo" "ruolo" "Statistiche ruolo" "dove trovo le statistiche del ruolo?" "/" "" "200" "/ruolo/stats" "In questa pagina posso aiutarti"
run_module_case "ruolo" "ruolo" "Import ruolo" "dove trovo l'import del ruolo?" "/" "" "200" "/ruolo/import" "In questa pagina posso aiutarti"

run_module_case "utenze" "utenze" "Import utenze" "dove trovo l'import utenze?" "/" "" "200" "/utenze/import" "In questa pagina posso aiutarti"
run_module_case "utenze" "utenze" "Anomalie visure" "dove vedo le anomalie delle visure routing?" "/" "" "200" "/utenze/visure-routing-anomalies" "In questa pagina posso aiutarti"

run_module_case "elaborazioni" "elaborazioni" "Visure" "dove trovo le visure?" "/" "" "200" "/elaborazioni/visure" "In questa pagina posso aiutarti"
run_module_case "elaborazioni" "elaborazioni" "ANPR" "dove trovo le elaborazioni anpr?" "/" "" "200" "/elaborazioni/anpr" "In questa pagina posso aiutarti"
run_module_case "elaborazioni" "elaborazioni" "Capacitas" "dove trovo capacitas?" "/" "" "200" "/elaborazioni/capacitas" "In questa pagina posso aiutarti"
run_module_case "elaborazioni" "elaborazioni" "Allineamento ADE" "dove trovo l'allineamento ade?" "/" "" "200" "/elaborazioni/ade-alignment" "In questa pagina posso aiutarti"
run_module_case "elaborazioni" "elaborazioni" "Autodoc" "dove trovo autodoc?" "/" "" "200" "/elaborazioni/autodoc" "In questa pagina posso aiutarti"

echo ""
echo "==> Riepilogo"
echo "Casi totali: $TOTAL_CASES"
echo "Casi falliti: $FAILED_CASES"
echo "Casi passati: $((TOTAL_CASES - FAILED_CASES))"
echo ""
echo "==> Riepilogo per modulo"

for i in "${!MODULE_NAMES[@]}"; do
  echo "${MODULE_NAMES[$i]}: passati $((MODULE_TOTALS[$i] - MODULE_FAILURES[$i]))/${MODULE_TOTALS[$i]}  falliti ${MODULE_FAILURES[$i]}"
done

if (( FAILED_CASES > 0 )); then
  exit 1
fi
