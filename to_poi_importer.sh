#!/bin/sh
set -e -v

# Assumes POI-Importer.github.io has been cloned in current directory
# git clone git@github.com:POI-Importer/POI-Importer.github.io.git
# also requires graceful-fs:
# sudo npm install osmtogeojson
# and that osmtogeojson has been installed.
# git clone git@github.com:tyrasd/osmtogeojson.git
# sudo npm install -g osmtogeojson
# osmtogeojson file.osm > file.geojson

# Create a 'large' .osm file with all kindergartens:
python barnehagefakta_osm.py -q --kommune ALL --output_filename POI-Importer.github.io/all.osm --cache_dir barnehagefakta_osm_data/data/
# convert to json and tile it
cd POI-Importer.github.io
osmtogeojson all.osm > data.json
node tile_geojson.js
