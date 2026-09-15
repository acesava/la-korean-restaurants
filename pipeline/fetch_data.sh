#!/usr/bin/env bash
# Re-download every raw input used by the pipeline (snapshots used in this repo were pulled 2026-09-14).
set -euo pipefail
cd "$(dirname "$0")"
UA="la-korean-restaurants/1.0"

# 1. LA County Environmental Health — Restaurant & Market Inventory (CSV, ~10 MB)
#    https://data.lacounty.gov/datasets/4f31c9a99e444a40a3806e3bbe7b5fdd
curl -sL -A "$UA" "https://www.arcgis.com/sharing/rest/content/items/4f31c9a99e444a40a3806e3bbe7b5fdd/data" -o county_inv.csv

# 2. Census TIGERweb boundaries: LA County (GEOID 06037) and City of Los Angeles (GEOID 0644000)
curl -s -A "$UA" "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query?where=GEOID%3D%2706037%27&outFields=NAME&returnGeometry=true&outSR=4326&f=geojson" -o lacounty.geojson
curl -s -A "$UA" "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4/query?where=GEOID%3D%270644000%27&outFields=NAME&returnGeometry=true&outSR=4326&f=geojson" -o lacity.geojson

# 3. OpenStreetMap via Overpass (query in q2.txt; overpass-api.de was overloaded, so a mirror was used)
curl -s -m 180 -A "$UA" --data-urlencode "data@q2.txt" "https://maps.mail.ru/osm/tools/overpass/api/interpreter" -o osm.json

# 4. Overture Maps Places, release 2026-08-19.0 (queried remotely with DuckDB)
python overture.py
