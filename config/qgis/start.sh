#!/bin/sh
set -eu

install -o www-data -g www-data -m 0600 \
  /srv/qgis/gaia-gis-platform.qgs \
  /var/lib/qgis/gaia-gis-platform.qgs

exec /usr/local/bin/start-xvfb-nginx.sh
