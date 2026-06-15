#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/install_gate_mobile_sync_timer.sh

Variabili opzionali:
  CED_PROJECT_DIR=/opt/gaia
  ENV_FILE=/opt/gaia/.env
  SYSTEMD_DIR=/etc/systemd/system
  UNIT_NAME=gaia-gate-mobile-sync

Lo script:
  - genera l'unita systemd service dal template repo
  - copia service e timer nella directory systemd
  - esegue daemon-reload
  - abilita e avvia subito il timer
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

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CED_PROJECT_DIR="${CED_PROJECT_DIR:-/opt/gaia}"
ENV_FILE="${ENV_FILE:-/opt/gaia/.env}"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
UNIT_NAME="${UNIT_NAME:-gaia-gate-mobile-sync}"
DOCKER_BIN="$(command -v docker || true)"
SERVICE_TEMPLATE="$ROOT_DIR/deploy/systemd/gaia-gate-mobile-sync.service.tpl"
TIMER_TEMPLATE="$ROOT_DIR/deploy/systemd/gaia-gate-mobile-sync.timer"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

require_cmd systemctl

if [[ -z "$DOCKER_BIN" ]]; then
  echo "Errore: docker non trovato nel PATH." >&2
  exit 1
fi

if [[ ! -f "$SERVICE_TEMPLATE" || ! -f "$TIMER_TEMPLATE" ]]; then
  echo "Errore: template systemd non trovato nel repository." >&2
  exit 1
fi

service_file="$TMP_DIR/$UNIT_NAME.service"
timer_file="$TMP_DIR/$UNIT_NAME.timer"

sed \
  -e "s|{{CED_PROJECT_DIR}}|$CED_PROJECT_DIR|g" \
  -e "s|{{ENV_FILE}}|$ENV_FILE|g" \
  -e "s|{{DOCKER_BIN}}|$DOCKER_BIN|g" \
  "$SERVICE_TEMPLATE" > "$service_file"
cp "$TIMER_TEMPLATE" "$timer_file"

install -D -m 0644 "$service_file" "$SYSTEMD_DIR/$UNIT_NAME.service"
install -D -m 0644 "$timer_file" "$SYSTEMD_DIR/$UNIT_NAME.timer"

systemctl daemon-reload
systemctl enable --now "$UNIT_NAME.timer"
systemctl status "$UNIT_NAME.timer" --no-pager
