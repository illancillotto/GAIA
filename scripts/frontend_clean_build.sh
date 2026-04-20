#!/bin/sh
set -eu

echo "[gaia] stopping frontend container to release mounted .next cache..."
docker compose stop frontend >/dev/null

echo "[gaia] running clean frontend build in ephemeral container..."
docker compose run --rm -e NODE_ENV=production frontend sh -lc 'mkdir -p /app/.next && find /app/.next -mindepth 1 -maxdepth 1 -exec rm -rf {} + && npm run build'

echo "[gaia] starting frontend container again..."
docker compose up -d frontend >/dev/null

echo "[gaia] clean frontend build completed."
