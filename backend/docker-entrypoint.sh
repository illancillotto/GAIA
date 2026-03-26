#!/bin/sh
set -eu

echo "Applying Alembic migrations..."
alembic upgrade head

echo "Starting service: $*"
exec "$@"
