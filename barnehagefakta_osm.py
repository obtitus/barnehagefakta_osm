#!/usr/bin/env python
# -*- coding: utf8

# Standard python imports
import re
import os
import datetime
import logging
logger = logging.getLogger('barnehagefakta')
# Non standard
import osmapis
# This project:
from barnehagefakta_get import barnehagefakta_get
from barnehageregister_nbrId import get_kommune, update_kommune

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

def create_osmtags(udir_tags, operator='', name=''):
    # See http://data.udir.no/baf/json-beskrivelse.html for a full list of expected keys

    lat, lon = udir_tags['koordinatLatLng']
    attribs = dict(lat=lat, lon=lon)
    # checks:
    if not(udir_tags['erBarnehage']):
        raise ValueError('Error: data says this is not a barnehage erBarnehage=%s' % udir_tags['erBarnehage'])
    if not(udir_tags['erAktiv']):
        raise ValueError('FIXME: erAktiv is False, what-to-do!')

    # opening_hours = ''
    # o_fra, o_til = parse_apningstid(udir_tags['apningstidFra']), parse_apningstid(udir_tags['apningstidTil'])
    # if o_fra is not None and o_til is not None:
    #     # fixme: should we always add "Mo-Fr" (Monday-Friday) and PH (public holiday)?
    #     # opening_hours = 'Mo-Fr {0}-{1}; PH off'.format(o_fra, o_til)
    #     # service_hours better?
    #     opening_hours = '{0}-{1}'.format(o_fra, o_til)    
    # opening_hours combined with udir_tags['type'] == 'åpen' could be moderately useful on the go.
    # add udir_tags['type'] to description:no ?

    # Consider parsing udir_tags['besoksAdresse']['adresselinje'] into addr:housenumber, addr:street
    # this could help when merging the data, since lat/lon is often incorrect.
    # addr_postcode = udir_tags['besoksAdresse']['postnr']
    # addr_city = udir_tags['besoksAdresse']['poststed']

    #'fee': udir_tags['kostpenger'] != 0, # needs to be combined with 'Pris for opphold', which is not present in the dataset
    
    operator_type = ''
    if udir_tags['eierform'] == 'Privat':
        operator_type = 'private'
    elif udir_tags['eierform'] == 'Kommunal':
        operator_type = 'public'
    else:
        logger.warning('Unknown "eierform=%s", fixme: consider using "erPrivatBarnehage=%s"',
                       udir_tags['eierform'], udir_tags['erPrivatBarnehage'])

    min_age, max_age = '', ''
    age = udir_tags['alder']
    try:
        min_age, max_age = re.split('[^\d.]+', age)
        min_age, max_age = int(min_age), int(max_age) # ensure ints (fixme: support float?):
    except ValueError as e:
        logger.warning('unable to parse "%s" into min and max age, %s', age, e)

    tags_contact = dict()
    if udir_tags['kontaktinformasjon'] is not None:
        tags_contact = {'contact:website': udir_tags['kontaktinformasjon']['url'],
                        'contact:phone': udir_tags['kontaktinformasjon']['telefon'],
                        'contact:email': udir_tags['kontaktinformasjon']['epost']}
    capacity = ''
    if udir_tags['indikatorDataBarnehage'] is not None:
        antallBarn = udir_tags['indikatorDataBarnehage']['antallBarn']
        capacity = int(antallBarn) # ensure int

    start_date = ''
    if udir_tags['opprettetDato'] != '':
        try:
            d = datetime.datetime.strptime(udir_tags['opprettetDato'], '%m/%d/%Y')
            start_date = datetime.date(year=d.year, month=d.month, day=d.day).isoformat()
        except Exception as e:
            logger.warning("Invalid date in udir_tags['opprettetDato'] = '%s'. %s", udir_tags['opprettetDato'], e)
            
    if name != '':
        assert name == udir_tags['navn'] # name is assumed to come from barnehageregister, check that it corresponds to barnehagefakta.
        
    osm_tags = {'amenity': 'kindergarten',
                'name': udir_tags['navn'],
                'no-barnehage:nsrid': udir_tags['nsrId'], # key-name suggestions?
#                'opening_hours': opening_hours,
                'operator': operator,
                'operator:type': operator_type,
                'min_age': min_age,
                'max_age': max_age,
                'capacity': capacity,
                'start_date': start_date}
    osm_tags.update(tags_contact)
    
    # cleanup, remove empty vlues and convert to string.
    remove_empty_values(osm_tags)
    values_to_str(osm_tags)

    # Create and return osmapis.Node and type
    node = osmapis.Node(attribs=attribs, tags=osm_tags)
    logger.info('Created node %s', node)
    return node, udir_tags['type']

def main(lst, output_filename, cache_dir):
    osm = osmapis.OSM()
    osm_familiebarnehage = osmapis.OSM()
    visited_ids = set()
    for item in lst:
        operator = ''
        name = ''
        # item can be either dictionary or simply items
        try:
            nbr_id = item['nbrId']
            operator = item['Eier']
            name = item['name']
        except TypeError:
            nbr_id = item

        if nbr_id in visited_ids:
            logger.warning('Already added %s', nbr_id)
        visited_ids.add(nbr_id)

        try:
            udir_tags = barnehagefakta_get(nbr_id, cache_dir=cache_dir)
            if udir_tags == {}: continue
            node, barnehage_type = create_osmtags(udir_tags, operator=operator, name=name)

            if barnehage_type == u'Familiebarnehage':
                osm_familiebarnehage.add(node)
            else:
                osm.add(node)
        except:
            logger.exception('Un-handled exception for nbr_id = %s', nbr_id)
            exit(1)
    
    osm.save(output_filename)
    if len(osm_familiebarnehage) != 0:
        base, ext = os.path.splitext(output_filename)
        osm_familiebarnehage.save(base + '_familiebarnehager' + ext)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Converts norwegian "barnehage"-data from "Utdanningdsdirektoratet Nasjonalt barnehageregister" to .osm format for import into openstreetmap.')
    parser.add_argument('--nbr_id', nargs='+', help='barnehagens unike id fra Nasjonalt barnehageregister.')
    parser.add_argument('--kommunenummer', nargs='+', help='Kommunenummer (e.g. 0213), consider using with --update_kommune')
    parser.add_argument('--update_kommune', default=False, action='store_true',
                        help='Updates/creates nsrIds for the given --kommunenummer (calls barnehageregister_nbrId.py)')
    parser.add_argument('--output_filename', default=None,
                        help='Specify output filename, defaults to "barnehagefakta.osm", for kommuner it will default to cache_dir/<nr>/barnehagefakta.osm')
    parser.add_argument('--cache_dir', default='data',
                        help='Specify directory for cached .json files, defaults to data/')
    # http://stackoverflow.com/a/20663028
    parser.add_argument('-d', '--debug', help="Print lots of debugging statements",
                        action="store_const", dest="loglevel", const=logging.DEBUG,
                        default=logging.DEBUG)
    parser.add_argument('-v', '--verbose', help="Be verbose",
                        action="store_const", dest="loglevel", const=logging.INFO)
    parser.add_argument('-q', '--quiet', help="Suppress non-warning messages.",
                        action="store_const", dest="loglevel", const=logging.WARNING)
    
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)
    
    if args.kommunenummer:      # list of kommuner given
        for kommune_id in args.kommunenummer:
            if args.update_kommune:
                update_kommune(kommune_id, cache_dir=args.cache_dir)

            k = get_kommune(kommune_id, cache_dir=args.cache_dir)
            
            cache_dir = os.path.join(args.cache_dir, kommune_id) # work inside kommune folder
            if args.output_filename is None:
                output_filename = os.path.join(cache_dir, 'barnehagefakta.osm')
            
            main(k, output_filename, cache_dir)
    if args.nbr_id:
        output_filename = args.output_filename
        if output_filename is None:
            output_filename = 'barnehagefakta.osm'
        main(args.nbr_id, output_filename, args.cache_dir)
