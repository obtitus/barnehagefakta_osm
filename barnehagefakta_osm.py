#!/usr/bin/env python
# -*- coding: utf8

# Standard python imports
import re
import datetime
import logging
logger = logging.getLogger('barnehagefakta')
# Non standard
import osmapis
# This project:
from barnehagefakta_get import barnehagefakta_get

def remove_empty_values(dct):
    """Remove all dictionary items where the value is '' or None."""
    for key in dct.keys():
        if dct[key] in ('', None):
            del dct[key]

def values_to_str(dct):
    """Convert all values to strings"""
    for key in dct.keys():
        if isinstance(dct[key], bool):
            if dct[key]:
                dct[key] = 'yes'
            else:
                dct[key] = 'no'
        elif isinstance(dct[key], basestring):
            pass
        else:
            dct[key] = str(dct[key])

def create_osmtags(udir_tags):
    # See http://data.udir.no/baf/json-beskrivelse.html for a full list of expected keys

    # First some special tags:
    lat, lon = udir_tags['koordinatLatLng']
    attribs = dict(lat=lat, lon=lon)
    # checks:
    if not(udir_tags['erBarnehage']):
        print 'Error: data says this is not a barnehage erBarnehage=%s' % udir_tags['erBarnehage']
        return ;
    if not(udir_tags['erAktiv']):
        print 'FIXME: erAktiv is False, what-to-do!'

    o_fra, o_til = udir_tags['apningstidFra'], udir_tags['apningstidTil']
    # ensure valid (fixme, function):
    hour, minute = o_fra.split(':')
    datetime.time(hour=int(hour), minute=int(minute))
    hour, minute = o_til.split(':')
    datetime.time(hour=int(hour), minute=int(minute))
    # fixme: should we always add "Mo-Fr" (Monday-Friday) and PH (public holiday)?
    # opening_hours combined with udir_tags['type'] == 'åpen' could be moderately useful on the go.
    opening_hours = 'Mo-Fr {0}-{1}; PH off'.format(o_fra, o_til)

    # Consider parsing udir_tags['besoksAdresse']['adresselinje'] into addr:housenumber, addr:street
    # this could help when merging the data, since lat/lon is often incorrect.
    # addr_postcode = udir_tags['besoksAdresse']['postnr']
    # addr_city = udir_tags['besoksAdresse']['poststed']

    # consider parsing udir_tags[u'orgnr'] to get the 'operator',
    # entire orgnr dataset can be found at http://data.brreg.no/oppslag/enhetsregisteret/enheter.xhtml
    # api:  http://data.brreg.no/enhetsregisteret/enhet/{orgnr}.{format}
    # or?:  http://data.brreg.no/enhetsregisteret/underenhet/987861649.json

    #'fee': udir_tags['kostpenger'] != 0, # needs to be combined with 'Pris for opphold', which is not present in the dataset    
    
    age = udir_tags['alder']
    min_age, max_age = re.split('[^\d]+', "1 - 5")
    # ensure ints:
    min_age, max_age = int(min_age), int(max_age)

    # 'normal' tags:
    tags = {'name': udir_tags['navn'],
            'contact:website': udir_tags['kontaktinformasjon']['url'],
            'contact:phone': udir_tags['kontaktinformasjon']['telefon'],
            'contact:email': udir_tags['kontaktinformasjon']['epost'],
            'capacity': udir_tags['indikatorDataBarnehage']['antallBarn'],
            'min_age':min_age,
            'max_age':max_age,
            'opening_hours':opening_hours}

    # cleanup
    remove_empty_values(tags)
    values_to_str(tags)

    # Create and return osmapis.Node
    node = osmapis.Node(attribs=attribs, tags=tags)
    logger.info('Created node %s', node)
    return node

def main(lst, output_filename, cache_dir):
    osm = osmapis.OSM()
    for nbr_id in lst:
        udir_tags = barnehagefakta_get(nbr_id, cache_dir=cache_dir)
        node = create_osmtags(udir_tags)
        osm.add(node)
    osm.save(output_filename)
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    import argparse
    parser = argparse.ArgumentParser(description='Converts norwegian "barnehage"-data from "Utdanningdsdirektoratet Nasjonalt barnehageregister" to .osm format for import into openstreetmap.')
    parser.add_argument('nbr_id', nargs='+', help='barnehagens unike id fra Nasjonalt barnehageregister.')
    parser.add_argument('--output_filename', default='barnehagefakta.osm',
                        help='Specify output filename, defaults to "barnehagefakta.osm"')
    parser.add_argument('--cache_dir', default='data',
                        help='Specify directory for cached .json files, defaults to data/')
    args = parser.parse_args()
    
    main(args.nbr_id, args.output_filename, args.cache_dir)
