.PHONY: clean test

test: test_update_osm test_conflate_osm

test_update_osm:
	nosetests --with-coverage --cover-tests --cover-erase --cover-branches --cover-package="barnehagefakta_osm,update_osm,update_osm_test" --cover-inclusive --cover-html --cover-html-dir=coverage update_osm_test.py

test_conflate_osm:
	python -m doctest -v conflate_osm.py

clean:
	rm -f *.pyc
	rm -f *~
	rm -rf coverage
