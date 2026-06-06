#!/bin/sh
set -eu

echo "Applying Alembic migrations..."
alembic upgrade heads

echo "Starting service: $*"
exec "$@"
