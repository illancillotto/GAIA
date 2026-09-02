#!/bin/sh
set -eu

install -o www-data -g www-data -m 0600 \
  /srv/qgis/gaia-gis-platform.qgs \
  /var/lib/qgis/gaia-gis-platform.qgs
install -o www-data -g www-data -m 0600 \
  /srv/qgis/pg_service.conf \
  /var/lib/qgis/pg_service.conf
# spawn-fcgi drops to www-data (HOME=/var/www) and does not keep PGSERVICEFILE.
install -o www-data -g www-data -m 0600 \
  /srv/qgis/pg_service.conf \
  /var/www/.pg_service.conf

exec /usr/local/bin/start-xvfb-nginx.sh
