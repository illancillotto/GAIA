#!/usr/bin/env sh

docker compose exec backend python scripts/scheduled_live_sync.py
