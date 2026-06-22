#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/setup-local-dev-gateway.sh
  ./scripts/setup-local-dev-gateway.sh --gateway-port 80
  ./scripts/setup-local-dev-gateway.sh --use-lan-domains
  ./scripts/setup-local-dev-gateway.sh --skip-hosts

Options:
  --gateway-port PORT   Host port for the shared local gateway. Default: 80
  --use-lan-domains     Also map gaia.lan, teti.lan and gaia-mobile.lan to 127.0.0.1 locally.
  --skip-hosts          Do not edit /etc/hosts; start only the shared gateway.
  --help                Show this help.

What it does:
  - ensures gaia.local, teti.local and gaia-mobile.local point to 127.0.0.1 in /etc/hosts
  - optionally shadows gaia.lan, teti.lan and gaia-mobile.lan to 127.0.0.1 on this machine only
  - starts the shared local gateway from docker-compose.local-gateway.yml
  - lets you use hostname-based URLs without exposing every stack directly on port 80
EOF
}

GATEWAY_PORT="80"
SKIP_HOSTS="false"
DOMAINS=("gaia.local" "teti.local" "gaia-mobile.local")
USE_LAN_DOMAINS="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --gateway-port)
      GATEWAY_PORT="${2:-}"
      shift 2
      ;;
    --use-lan-domains)
      USE_LAN_DOMAINS="true"
      shift
      ;;
    --skip-hosts)
      SKIP_HOSTS="true"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "$USE_LAN_DOMAINS" == "true" ]]; then
  DOMAINS+=("gaia.lan" "teti.lan" "gaia-mobile.lan")
fi

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Comando richiesto non trovato: $1" >&2
    exit 1
  fi
}

require_command docker
if [[ "$SKIP_HOSTS" != "true" ]]; then
  require_command grep
  require_command mktemp
  require_command sudo

  tmp_hosts="$(mktemp)"
  cleanup() {
    rm -f "$tmp_hosts"
  }
  trap cleanup EXIT

  cp /etc/hosts "$tmp_hosts"
  hosts_changed="false"

  for domain in "${DOMAINS[@]}"; do
    if grep -Eq "^[[:space:]]*127\\.0\\.0\\.1[[:space:]]+.*\\b${domain//./\\.}\\b" /etc/hosts; then
      echo "[gaia] /etc/hosts contiene gia ${domain} -> 127.0.0.1"
      continue
    fi

    printf '\n127.0.0.1 %s\n' "$domain" >>"$tmp_hosts"
    echo "[gaia] aggiunta mapping hosts: 127.0.0.1 ${domain}"
    hosts_changed="true"
  done

  if [[ "$hosts_changed" == "true" ]]; then
    sudo cp "$tmp_hosts" /etc/hosts
  fi
else
  echo "[gaia] salto aggiornamento /etc/hosts (--skip-hosts)"
fi

echo "[gaia] avvio gateway locale condiviso sulla porta host ${GATEWAY_PORT}..."
LOCAL_DEV_GATEWAY_PORT="$GATEWAY_PORT" docker compose -f docker-compose.local-gateway.yml up -d

if [[ "$GATEWAY_PORT" == "80" ]]; then
  echo "[gaia] domini disponibili:"
  echo "  - http://gaia.local"
  echo "  - http://teti.local"
  echo "  - http://gaia-mobile.local"
  if [[ "$USE_LAN_DOMAINS" == "true" ]]; then
    echo "  - http://gaia.lan"
    echo "  - http://teti.lan"
    echo "  - http://gaia-mobile.lan"
  fi
else
  echo "[gaia] domini disponibili:"
  echo "  - http://gaia.local:${GATEWAY_PORT}"
  echo "  - http://teti.local:${GATEWAY_PORT}"
  echo "  - http://gaia-mobile.local:${GATEWAY_PORT}"
  if [[ "$USE_LAN_DOMAINS" == "true" ]]; then
    echo "  - http://gaia.lan:${GATEWAY_PORT}"
    echo "  - http://teti.lan:${GATEWAY_PORT}"
    echo "  - http://gaia-mobile.lan:${GATEWAY_PORT}"
  fi
fi

echo "[gaia] prerequisito: gli stack GAIA, TETI e GAIA-mobile devono restare attivi sulle rispettive porte 8080, 8085 e 5173."
