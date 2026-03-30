#!/bin/sh
set -eu

LOCKFILE_HASH_FILE="node_modules/.package-lock.hash"

mkdir -p node_modules

CURRENT_HASH="$(sha256sum package-lock.json package.json | sha256sum | cut -d' ' -f1)"
STORED_HASH=""

if [ -f "$LOCKFILE_HASH_FILE" ]; then
  STORED_HASH="$(cat "$LOCKFILE_HASH_FILE")"
fi

if [ ! -d node_modules/.bin ] || [ "$CURRENT_HASH" != "$STORED_HASH" ]; then
  echo "[frontend-dev] dependencies changed, running npm install..."
  npm install
  printf '%s' "$CURRENT_HASH" > "$LOCKFILE_HASH_FILE"
fi

exec npm run dev
