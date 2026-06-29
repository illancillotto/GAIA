#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAINTENANCE_DIR="${MAINTENANCE_DIR:-$ROOT_DIR/runtime-data/nginx-maintenance}"
FLAG_PATH="$MAINTENANCE_DIR/on"

mkdir -p "$MAINTENANCE_DIR"
touch "$FLAG_PATH"

echo "[gaia] maintenance mode enabled: $FLAG_PATH"
