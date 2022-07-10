#!/bin/sh
set -e -v

#python=/opt/local/bin/python2.7
#python=(source barnehagefakta_osm_data/venv/bin/activate; python)

osmtogeojson=/opt/local/bin/osmtogeojson
node=/opt/local/bin/node
git=/usr/bin/git
# Assumes POI-Importer.github.io has been cloned in current directory
POI="POI-Importer.github.io"
OUTPUTDIR=datasets/norge-barnehagefakta
# git clone --recursive https://github.com/POI-Importer/POI-Importer.github.io.git
# also requires graceful-fs, mkdirp, rimraf, command-line-args and osmtogeojson
# cd POI-Importer.github.io
# sudo npm install graceful-fs
# sudo npm install mkdirp
# sudo npm install rimraf
# sudo npm install command-line-args
# sudo npm install -g osmtogeojson
# cd ..

# Create a 'large' .osm file with all kindergartens:
python barnehagefakta_osm.py -s --kommune ALL --output_filename $POI/$OUTPUTDIR/norge_barnehagefakta.osm --cache_dir barnehagefakta_osm_data/data/
# convert to json and tile it
cd $POI
$node $osmtogeojson $OUTPUTDIR/norge_barnehagefakta.osm > $OUTPUTDIR/norge_barnehagefakta.json
$node tile_geojson.js -d $OUTPUTDIR/norge_barnehagefakta.json -r $OUTPUTDIR
#$node tile_geojson.js $OUTPUTDIR/norge_barnehagefakta.json  $OUTPUTDIR
cd $OUTPUTDIR
$git add -A data/
$git commit -am "auto data update" || true
$git push || true

# update submodule
cd ../
$git commit -am "auto submodule update" || true
$git push || true
