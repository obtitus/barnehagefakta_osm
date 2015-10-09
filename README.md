# Barnehagefakta to Openstreetmap
Script for updating/importing/conflating data about kindergartens ("barnehager") in Norway to openstreetmap.

For information about the dataset, go to http://data.udir.no/baf/

For information about the import, go to http://wiki.openstreetmap.org/wiki/Key:no-barnehage:nsrid

To view/download the output, go to http://obtitus.github.io/barnehagefakta_osm_data/

## Overview of files
* `barnehagefakta_get.py` is intended to be a general script for downloading
  (with a local cache) json files from http://barnehagefakta.no/api/barnehage/<nsrid>.

* The api does not currently give a list of nsrids so
  `barnehageregister_nbrId.py` parses https://nbr.udir.no/sok for a given kommune-nr.
  The file kommunenummer.py contains a dictionary of kommune-nr and name.

* `barnehagefakta_osm.py` is the main script to use for openstreetmap related tasks.
  use `--help` for usage.

* `update_osm.py` is used for keeping the openstreetmap data up-to date.
  You need to supply a `mypasswords.py` file with your openstreetmap username and password
  (see `mypasswords_template.py`).

* `generate_html.py` is used for generating http://obtitus.github.io/barnehagefakta_osm_data/
  (and is the script in the most need of a re-write)
  
## Dependencies
* osmapis from https://github.com/xificurk/osmapis

  `git clone git@github.com:xificurk/osmapis.git`
  
* requests (http://www.python-requests.org)

  `pip install requests`
  
* BeautifulSoup (http://www.crummy.com/software/BeautifulSoup/)

  `pip install beautifulsoup4`
  
* Jinja2 (http://jinja.pocoo.org) required by `generate_html.py`

  `pip install jinja2`