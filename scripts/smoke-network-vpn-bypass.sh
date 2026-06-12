#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/smoke-network-vpn-bypass.sh

Smoke test autenticato della console Network "VPN / Proxy Bypass".

Variabili:
  BASE_URL=http://localhost:8080/api   Base URL API da verificare
  ENV_FILE=.env                        File env da cui leggere le credenziali bootstrap admin
  ADMIN_USERNAME=admin                 Override username login
  ADMIN_PASSWORD=...                   Override password login

Controlli eseguiti:
  1. health endpoint
  2. login admin
  3. ingest syslog sintetico e avanzamento max(observed_at)
  4. /network/vpn-bypass/summary
  5. /network/vpn-bypass/arp-timeline?window_hours=168&limit=10
  6. /network/detection-watchlist
  7. /network/tracking?window_hours=168
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Errore: comando richiesto non trovato: $1" >&2
    exit 1
  fi
}

read_env_value() {
  local env_file="$1"
  local key="$2"
  python3 - "$env_file" "$key" <<'PY'
from pathlib import Path
import sys

env_file = Path(sys.argv[1])
key = sys.argv[2]

if not env_file.exists():
    sys.exit(1)

for raw_line in env_file.read_text().splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    current_key, value = line.split("=", 1)
    if current_key == key:
        print(value)
        break
else:
    sys.exit(1)
PY
}

require_cmd curl
require_cmd python3
require_cmd docker

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BASE_URL="${BASE_URL:-http://localhost:8080/api}"
ENV_FILE="${ENV_FILE:-.env}"
ADMIN_USERNAME="${ADMIN_USERNAME:-}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
POSTGRES_DB="${POSTGRES_DB:-}"
POSTGRES_USER="${POSTGRES_USER:-}"
SYSLOG_UDP_HOST="${SYSLOG_UDP_HOST:-127.0.0.1}"
SYSLOG_UDP_PORT="${SYSLOG_UDP_PORT:-5514}"
SYSLOG_WAIT_SECONDS="${SYSLOG_WAIT_SECONDS:-5}"

if [[ -z "$ADMIN_USERNAME" ]]; then
  ADMIN_USERNAME="$(read_env_value "$ENV_FILE" "BOOTSTRAP_ADMIN_USERNAME")"
fi
if [[ -z "$ADMIN_PASSWORD" ]]; then
  ADMIN_PASSWORD="$(read_env_value "$ENV_FILE" "BOOTSTRAP_ADMIN_PASSWORD")"
fi
if [[ -z "$POSTGRES_DB" ]]; then
  POSTGRES_DB="$(read_env_value "$ENV_FILE" "POSTGRES_DB")"
fi
if [[ -z "$POSTGRES_USER" ]]; then
  POSTGRES_USER="$(read_env_value "$ENV_FILE" "POSTGRES_USER")"
fi

db_scalar() {
  local sql="$1"
  docker exec gaia-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "$sql"
}

echo "==> Smoke test health"
curl -fsS "${BASE_URL}/health" >/dev/null

echo "==> Smoke test login admin"
LOGIN_PAYLOAD="$(
  python3 - "$ADMIN_USERNAME" "$ADMIN_PASSWORD" <<'PY'
import json
import sys

print(json.dumps({"username": sys.argv[1], "password": sys.argv[2]}))
PY
)"
TOKEN="$(
  curl -fsS "${BASE_URL}/auth/login" \
    -H 'Content-Type: application/json' \
    -d "${LOGIN_PAYLOAD}" \
  | python3 -c 'import json,sys; payload=json.load(sys.stdin); token=payload.get("access_token"); assert token, "access_token non presente nella risposta login"; print(token)'
)"

auth_get() {
  local path="$1"
  curl -fsS "${BASE_URL}${path}" -H "Authorization: Bearer ${TOKEN}"
}

echo "==> Smoke test ingest syslog sintetico"
BEFORE_MAX_OBSERVED_AT="$(db_scalar "select coalesce(max(observed_at)::text,'') from network_firewall_events;")"
SYSLOG_MESSAGE="$(
  python3 - <<'PY'
from datetime import datetime, timezone

timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
print(
    f'<134>{timestamp} smoke-test-gaia '
    'device_name="XGS87" '
    'log_type="Content Filtering" '
    'log_component="HTTP" '
    'log_subtype="Allowed" '
    'priority="Info" '
    'src_ip=192.168.1.250 '
    'dst_ip=8.8.8.8 '
    'domain=smoke-test-vpn.example '
    'url=https://smoke-test-vpn.example/check '
    'message="GAIA smoke test syslog ingest"'
)
PY
)"
python3 - "$SYSLOG_UDP_HOST" "$SYSLOG_UDP_PORT" "$SYSLOG_MESSAGE" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
payload = sys.argv[3].encode("utf-8")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(payload, (host, port))
sock.close()
PY
AFTER_MAX_OBSERVED_AT="$BEFORE_MAX_OBSERVED_AT"
for _ in $(seq 1 "$SYSLOG_WAIT_SECONDS"); do
  sleep 1
  AFTER_MAX_OBSERVED_AT="$(db_scalar "select coalesce(max(observed_at)::text,'') from network_firewall_events;")"
  if [[ -n "$AFTER_MAX_OBSERVED_AT" && "$AFTER_MAX_OBSERVED_AT" != "$BEFORE_MAX_OBSERVED_AT" ]]; then
    break
  fi
done
if [[ -z "$AFTER_MAX_OBSERVED_AT" || "$AFTER_MAX_OBSERVED_AT" == "$BEFORE_MAX_OBSERVED_AT" ]]; then
  echo "Errore: il max(observed_at) di network_firewall_events non e' avanzato dopo l'invio syslog." >&2
  exit 1
fi
echo "syslog ingest ok: max(observed_at) $BEFORE_MAX_OBSERVED_AT -> $AFTER_MAX_OBSERVED_AT"

echo "==> Smoke test /network/vpn-bypass/summary"
auth_get "/network/vpn-bypass/summary" \
  | python3 -c 'import json,sys; payload=json.load(sys.stdin); required={"total_subjects","vpn_subjects","proxy_subjects","tor_subjects","encrypted_dns_subjects","total_suspicious_events","open_alerts","watchlist_rules"}; missing=sorted(required.difference(payload)); assert not missing, f"summary incompleto, mancano: {'"'"', '"'"'.join(missing)}"; print(f"summary ok: subjects={payload['"'"'total_subjects'"'"']} suspicious={payload['"'"'total_suspicious_events'"'"']}")'

echo "==> Smoke test /network/vpn-bypass/arp-timeline?window_hours=168&limit=10"
auth_get "/network/vpn-bypass/arp-timeline?window_hours=168&limit=10" \
  | python3 -c 'import json,sys; payload=json.load(sys.stdin); assert isinstance(payload, list), "arp timeline non e'"'"' una lista"; print(f"arp timeline ok: items={len(payload)}")'

echo "==> Smoke test /network/detection-watchlist"
auth_get "/network/detection-watchlist" \
  | python3 -c 'import json,sys; payload=json.load(sys.stdin); assert isinstance(payload, list), "watchlist non e'"'"' una lista"; print(f"watchlist ok: rules={len(payload)}")'

echo "==> Smoke test /network/tracking?window_hours=168"
auth_get "/network/tracking?window_hours=168" \
  | python3 -c 'import json,sys; payload=json.load(sys.stdin); assert isinstance(payload, list), "tracking non e'"'"' una lista"; print(f"tracking ok: subjects={len(payload)}")'

echo "Smoke test Network VPN bypass completato."
