#!/bin/bash
set -euo pipefail

SHAPEFILE="${1:?Usage: $0 <path/to/shapefile.shp>}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_DB="${POSTGRES_DB:-gaia}"
POSTGRES_USER="${POSTGRES_USER:-gaia}"
GAIA_API="${GAIA_API:-http://localhost:8000}"
STAGING_TABLE="${STAGING_TABLE:-cat_particelle_staging}"
SOURCE_SRID="${SOURCE_SRID:-3003}"

if [ -z "${POSTGRES_PASSWORD:-}" ]; then
  echo "POSTGRES_PASSWORD non impostata."
  exit 1
fi

if [ -z "${GAIA_ADMIN_TOKEN:-}" ]; then
  echo "GAIA_ADMIN_TOKEN non impostato."
  exit 1
fi

PG_CONN="PG:host=$POSTGRES_HOST dbname=$POSTGRES_DB user=$POSTGRES_USER password=$POSTGRES_PASSWORD"

echo "=== GAIA Catasto — Import Shapefile ==="
echo "File: $SHAPEFILE"
echo "Staging: $STAGING_TABLE"
echo "Proiezione: EPSG:$SOURCE_SRID → EPSG:4326"
echo ""

ogr2ogr \
  -f PostgreSQL "$PG_CONN" \
  "$SHAPEFILE" \
  -nln "$STAGING_TABLE" \
  -nlt MULTIPOLYGON \
  -s_srs "EPSG:$SOURCE_SRID" \
  -t_srs EPSG:4326 \
  -overwrite \
  -progress

echo ""
echo "Shapefile caricato in staging. Avvio finalize via API..."
curl -sf -X POST "$GAIA_API/catasto/import/shapefile/finalize" \
  -H "Authorization: Bearer $GAIA_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  | python3 -m json.tool

echo "=== Import completato ==="

