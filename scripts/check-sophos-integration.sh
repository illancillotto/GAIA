#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/check-sophos-integration.sh

Variabili opzionali:
  API_BASE_URL=http://localhost:8080/api
  FIREWALL_ID=1
  TOKEN=<jwt>

Controlli eseguiti:
  - stato container sophos-syslog e sophos-snmp
  - ultime righe di log dei collector
  - GET /network/firewalls
  - GET /network/firewalls/{id}/events
  - GET /network/firewalls/{id}/metrics
  - POST /network/firewalls/{id}/metrics/poll

Se TOKEN non e impostato, lo script esegue solo i controlli Docker/log.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

API_BASE_URL="${API_BASE_URL:-http://localhost:8080/api}"
FIREWALL_ID="${FIREWALL_ID:-1}"
TOKEN="${TOKEN:-}"

echo "==> Container stato"
docker compose ps sophos-syslog sophos-snmp backend || true

echo
echo "==> Log sophos-syslog (tail 40)"
docker compose logs --tail=40 sophos-syslog || true

echo
echo "==> Log sophos-snmp (tail 40)"
docker compose logs --tail=40 sophos-snmp || true

if [[ -z "$TOKEN" ]]; then
  echo
  echo "TOKEN non impostato: salto i controlli API."
  exit 0
fi

AUTH_HEADER="Authorization: Bearer $TOKEN"

echo
echo "==> GET /network/firewalls"
curl --fail --silent --show-error \
  -H "$AUTH_HEADER" \
  "$API_BASE_URL/network/firewalls" | python3 -m json.tool

echo
echo "==> GET /network/firewalls/$FIREWALL_ID/events"
curl --fail --silent --show-error \
  -H "$AUTH_HEADER" \
  "$API_BASE_URL/network/firewalls/$FIREWALL_ID/events?limit=10" | python3 -m json.tool

echo
echo "==> GET /network/firewalls/$FIREWALL_ID/metrics"
curl --fail --silent --show-error \
  -H "$AUTH_HEADER" \
  "$API_BASE_URL/network/firewalls/$FIREWALL_ID/metrics?limit=10" | python3 -m json.tool

echo
echo "==> POST /network/firewalls/$FIREWALL_ID/metrics/poll"
curl --fail --silent --show-error \
  -X POST \
  -H "$AUTH_HEADER" \
  "$API_BASE_URL/network/firewalls/$FIREWALL_ID/metrics/poll" | python3 -m json.tool
