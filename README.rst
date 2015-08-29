===============================================
                  Barnehagefakta to Openstreetmap
===============================================
Script for importing/conflating data about kindergartens ("barnehager") in Norway to openstreetmap.

For information about the dataset, go to http://data.udir.no/baf/
For information about the import, go to <fixme:link to wiki>

Overview of files
=================
* barnehagefakta_get.py is intended to be a general script for downloading
  (with a local cache) json files from http://barnehagefakta.no/api/barnehage/<nsrid>.

* The api does not currently give a list of nsrids so
  barnehageregister_nbrId.py parses https://nbr.udir.no/sok for a given kommune-nr.

* barnehagefakta_osm.py is the main script to use for openstreetmap related tasks.
  use --help for usage.

Dependencies
============
* osmapis from https://github.com/xificurk/osmapis
* requests: http://www.python-requests.org
  `pip install requests`
* BeautifulSoup: http://www.crummy.com/software/BeautifulSoup/
  `pip install beautifulsoup4`
  
