#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/setup-local-domain.sh
  ./scripts/setup-local-domain.sh --domain gaia.lan --ip 127.0.0.1 --env-file .env --port 8080

Options:
  --domain NAME     Local domain to register. Default: gaia.lan
  --ip ADDRESS      IP to map in /etc/hosts. Default: 127.0.0.1
  --env-file PATH   Env file to update/create. Default: .env
  --port PORT       Public nginx port used locally. Default: 8080
  --help            Show this help.

What it does:
  - ensures "<ip> <domain>" exists in /etc/hosts
  - ensures BACKEND_CORS_ORIGINS in the env file includes localhost and the local domain
  - reminds you which local URL to use and when port 80 is not viable
EOF
}

DOMAIN="gaia.lan"
IP_ADDRESS="127.0.0.1"
ENV_FILE=".env"
PORT="8080"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)
      DOMAIN="${2:-}"
      shift 2
      ;;
    --ip)
      IP_ADDRESS="${2:-}"
      shift 2
      ;;
    --env-file)
      ENV_FILE="${2:-}"
      shift 2
      ;;
    --port)
      PORT="${2:-}"
      shift 2
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

if [[ -z "$DOMAIN" || -z "$IP_ADDRESS" || -z "$ENV_FILE" || -z "$PORT" ]]; then
  echo "Dominio, IP, env file e porta devono essere valorizzati." >&2
  exit 1
fi

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Comando richiesto non trovato: $1" >&2
    exit 1
  fi
}

require_command grep
require_command mktemp
require_command python3
require_command sudo

hosts_line="${IP_ADDRESS} ${DOMAIN}"
if grep -Eq "^[[:space:]]*${IP_ADDRESS//./\\.}[[:space:]]+.*\\b${DOMAIN//./\\.}\\b" /etc/hosts; then
  echo "[gaia] /etc/hosts contiene gia ${DOMAIN} -> ${IP_ADDRESS}"
else
  tmp_hosts="$(mktemp)"
  trap 'rm -f "$tmp_hosts"' EXIT
  cp /etc/hosts "$tmp_hosts"
  printf '\n%s\n' "$hosts_line" >>"$tmp_hosts"
  echo "[gaia] aggiunta mapping hosts: $hosts_line"
  sudo cp "$tmp_hosts" /etc/hosts
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[gaia] creo $ENV_FILE da .env.example"
  cp .env.example "$ENV_FILE"
fi

python3 - "$ENV_FILE" "$DOMAIN" "$PORT" <<'PY'
from pathlib import Path
import sys

env_path = Path(sys.argv[1])
domain = sys.argv[2]
port = sys.argv[3]

required = [
    "http://localhost:3000",
    "http://localhost:8080",
    f"http://{domain}",
    f"http://{domain}:{port}",
]

lines = env_path.read_text(encoding="utf-8").splitlines()
updated = False
for idx, line in enumerate(lines):
    if not line.startswith("BACKEND_CORS_ORIGINS="):
        continue
    raw_value = line.split("=", 1)[1]
    tokens = [token.strip() for token in raw_value.split(",") if token.strip()]
    merged = []
    for token in tokens + required:
        if token not in merged:
            merged.append(token)
    lines[idx] = f"BACKEND_CORS_ORIGINS={','.join(merged)}"
    updated = True
    break

if not updated:
    lines.append(f"BACKEND_CORS_ORIGINS={','.join(required)}")

env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

echo "[gaia] aggiornato $ENV_FILE con BACKEND_CORS_ORIGINS compatibili con $DOMAIN"
if [[ "$PORT" == "80" ]]; then
  echo "[gaia] puoi raggiungere GAIA su http://${DOMAIN}"
else
  echo "[gaia] puoi raggiungere GAIA su http://${DOMAIN}:${PORT}"
  echo "[gaia] nota: su host condivisi con altri stack locali conviene mantenere porte distinte."
  echo "[gaia] usa la porta 80 solo se GAIA e l'unico servizio esposto oppure dietro un reverse proxy unico."
fi
