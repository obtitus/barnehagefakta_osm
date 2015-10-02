.PHONY: clean test

test:
	nosetests --with-coverage --cover-tests --cover-erase --cover-branches --cover-package="barnehagefakta_osm,update_osm,update_osm_test" --cover-inclusive --cover-html --cover-html-dir=coverage update_osm_test.py 

clean:
	rm -f *.pyc
	rm -f *~
	rm -rf coverage
