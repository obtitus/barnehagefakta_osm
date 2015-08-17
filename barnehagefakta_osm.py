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

def parse_apningstid(apningstid):
    try:
        hour, minute = apningstid.split(':')
        d = datetime.time(hour=int(hour), minute=int(minute))
        return d.strftime('%H:%M')
    except Exception as e:
        logger.warning('Error when parsing apningstid = "%s". %s', apningstid, e)
        return None

def create_osmtags(udir_tags):
    # See http://data.udir.no/baf/json-beskrivelse.html for a full list of expected keys

    osm_tags = dict()
    osm_tags['name'] = udir_tags['navn']

    lat, lon = udir_tags['koordinatLatLng']
    attribs = dict(lat=lat, lon=lon)
    # checks:
    if not(udir_tags['erBarnehage']):
        raise ValueError('Error: data says this is not a barnehage erBarnehage=%s' % udir_tags['erBarnehage'])
    if not(udir_tags['erAktiv']):
        raise ValueError('FIXME: erAktiv is False, what-to-do!')

    o_fra, o_til = parse_apningstid(udir_tags['apningstidFra']), parse_apningstid(udir_tags['apningstidTil'])
    if o_fra is not None and o_til is not None:
        # fixme: should we always add "Mo-Fr" (Monday-Friday) and PH (public holiday)?
        # opening_hours = 'Mo-Fr {0}-{1}; PH off'.format(o_fra, o_til)
        # service_hours better?
        osm_tags['opening_hours'] = '{0}-{1}'.format(o_fra, o_til)    
    # opening_hours combined with udir_tags['type'] == 'åpen' could be moderately useful on the go.

    # Consider parsing udir_tags['besoksAdresse']['adresselinje'] into addr:housenumber, addr:street
    # this could help when merging the data, since lat/lon is often incorrect.
    # addr_postcode = udir_tags['besoksAdresse']['postnr']
    # addr_city = udir_tags['besoksAdresse']['poststed']

    #'fee': udir_tags['kostpenger'] != 0, # needs to be combined with 'Pris for opphold', which is not present in the dataset
    
    # consider parsing udir_tags[u'orgnr'] to get the 'operator',
    # entire orgnr dataset can be found at http://data.brreg.no/oppslag/enhetsregisteret/enheter.xhtml
    # api:  http://data.brreg.no/enhetsregisteret/enhet/{orgnr}.{format}
    # or?:  http://data.brreg.no/enhetsregisteret/underenhet/987861649.json

    if udir_tags['eierform'] == 'Privat':
        osm_tags['operator:type'] = 'private'
    elif udir_tags['eierform'] == 'Kommunal':
        osm_tags['operator:type'] = 'public'
    else:
        logger.warning('Unknown "eierform=%s"', udir_tags['eierform'])
    
    age = udir_tags['alder']
    min_age, max_age = re.split('[^\d]+', "1 - 5")
    # ensure ints (fixme: support float?):
    osm_tags['min_age'], osm_tags['max_age'] = int(min_age), int(max_age)

    try:
        tags_contact = {'contact:website': udir_tags['kontaktinformasjon']['url'],
                        'contact:phone': udir_tags['kontaktinformasjon']['telefon'],
                        'contact:email': udir_tags['kontaktinformasjon']['epost']}
        osm_tags.update(tags_contact)
    except Exception as e:
        logger.warning('Error when parsing kontaktinformasjon. %s', e)
    try:
        osm_tags['capacity'] = int(udir_tags['indikatorDataBarnehage']['antallBarn'])
    except Exception as e:
        logger.warning('Error when parsing antallBarn. %s', e)

    # cleanup
    remove_empty_values(osm_tags)
    values_to_str(osm_tags)

    # Create and return osmapis.Node
    node = osmapis.Node(attribs=attribs, tags=osm_tags)
    logger.info('Created node %s', node)
    return node

def main(lst, output_filename, cache_dir):
    osm = osmapis.OSM()
    for nbr_id in lst:
        try:
            udir_tags = barnehagefakta_get(nbr_id, cache_dir=cache_dir)
            node = create_osmtags(udir_tags)
            osm.add(node)
        except:
            logger.exception('Un-handled exception for nbr_id = %s', nbr_id)
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
