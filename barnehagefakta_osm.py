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
from barnehagefakta_get import barnehagefakta_get, NotFoundException
from barnehageregister_nbrId import get_kommune, update_kommune
from kommunenummer import kommunenummer
import file_util

# global
reg_phone = re.compile('((0047)?|(\+47)?)([- _0-9]+)')

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

def add_country_code(input_dict, key, inplace=False):
    '''Does nothing if key is not in input_dict, otherwise, assume key points to a
    legal norwegian phone number and adds the '+47 ' prefix.
    note: this is not a very strict test, 
    but we want to ensure the number is mostly integers and does not already have the +47 prefix.
    inspired by:
    from http://begrep.difi.no/Felles/mobiltelefonnummer: "^\\+?[- _0-9]+$"
    from http://blog.kjempekjekt.com/2011/12/23/regex/: /^((0047)?|(\+47)?|(47)?)\d{8}$/
    does: ((0047)?|(\+47)?)([- _0-9]+)
    '''
    if key not in input_dict:
        return input_dict
    
    if inplace:
        d = input_dict
    else:
        d = dict(input_dict)
    
    reg = reg_phone.match(d[key])
    if reg is not None:
        # all okey, lets add +47
        d[key] = '+47 ' + reg.group(4)
    else:
        logger.warning('Possibly a invalid phone number: "%s", removing', d[key])
        del d[key]
    
    return d

def create_osmtags(udir_tags, operator='', name=''):
    # See http://data.udir.no/baf/json-beskrivelse.html for a full list of expected keys
    nsrId = int(udir_tags['nsrId']) # ensure int
    
    lat, lon = udir_tags['koordinatLatLng']
    attribs = dict(lat=lat, lon=lon)
    # checks:
    if not(udir_tags['erBarnehage']):
        raise ValueError('Error: %d data says this is not a barnehage erBarnehage=%s' % (nsrId, udir_tags['erBarnehage']))
    if not(udir_tags['erAktiv']):
        raise ValueError('FIXME: %d erAktiv is False, what-to-do!' % nsrId)

    # It was decided to not include opening_hours
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
        logger.warning('%d, Unknown "eierform=%s", fixme: consider using "erPrivatBarnehage=%s"',
                       nsrId, udir_tags['eierform'], udir_tags['erPrivatBarnehage'])

    min_age, max_age = '', ''
    age = udir_tags['alder']
    if age != '':
        try:
            min_age, max_age = re.split('[^\d.]+', age)
            min_age, max_age = int(min_age), int(max_age) # ensure ints (fixme: support float?):
        except ValueError as e:
            logger.warning('%d Unable to parse "%s" into min and max age, %s', nsrId, age, e)

    tags_contact = dict()
    if udir_tags['kontaktinformasjon'] is not None:
        tags_contact = {'contact:website': udir_tags['kontaktinformasjon']['url'],
                        'contact:phone': udir_tags['kontaktinformasjon']['telefon'],
                        'contact:email': udir_tags['kontaktinformasjon']['epost']}
    capacity = ''
    if udir_tags['indikatorDataBarnehage'] is not None:
        antallBarn = udir_tags['indikatorDataBarnehage']['antallBarn']
        if antallBarn is not None:
            capacity = int(antallBarn) # ensure int


    start_date = ''
    if udir_tags['opprettetDato'] != '':
        try:
            d = datetime.datetime.strptime(udir_tags['opprettetDato'], '%m/%d/%Y')
            start_date = datetime.date(year=d.year, month=d.month, day=d.day).isoformat()
        except Exception as e:
            logger.warning("%d Invalid date in udir_tags['opprettetDato'] = '%s'. %s", nsrId, udir_tags['opprettetDato'], e)
            
    if name != '':
        #assert name == udir_tags['navn'], 'name="%s", udir_tags["navn"]="%s"' % (name, udir_tags['navn']) # name is assumed to come from barnehageregister, check that it corresponds to barnehagefakta.
        if name != udir_tags['navn']:
            logger.warning(('The name from https://nbr.udir.no/enhet/{id} '
                            'differ from http://barnehagefakta.no/api/barnehage/{id},'
                            '"{nbr}" != "{barnehagefakta}"').format(
                                id=nsrId, barnehagefakta=udir_tags['navn'].encode('utf8'), nbr=name.encode('utf8')))
        
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
    
    # cleanup, remove empty values and convert to string.
    remove_empty_values(osm_tags)
    values_to_str(osm_tags)
    
    # if we still have a phone number, add a +47, ref issue #1
    add_country_code(osm_tags, key='contact:phone', inplace=True)
    
    # Create and return osmapis.Node and type
    node = osmapis.Node(attribs=attribs, tags=osm_tags)
    logger.debug('%d, Created node %s', nsrId, node)
    return node, udir_tags['type']

def main(lst, output_filename, cache_dir, osm=None, osm_familiebarnehage=None, save=True):
    """if osm and osm_familiebarnehage are given, they will be appended to.
    Ensure save is True to save the files (only needed on the last iteration)"""
    
    base, ext = os.path.splitext(output_filename)
    output_filename_familiebarnehager = base + '_familiebarnehager' + ext
    
    if osm is None:
        osm = osmapis.OSM()

    if osm_familiebarnehage is None:
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
        except NotFoundException as e:
            logger.warning(('Kindergarten "{name}" https://nbr.udir.no/enhet/{id}'
                            ', returned 404 at http://barnehagefakta.no/api/barnehage/{id}. '
                            'The kindergarten is probably discontinued.').format(
                                name=name.encode('utf8'), id=nbr_id))
        except:
            logger.exception('Un-handled exception for nbr_id = %s, skipping', nbr_id)
            exit(1)
            return osm, osm_familiebarnehage

    if save and len(osm) != 0:
        osm.save(output_filename)
    if save and len(osm_familiebarnehage) != 0:
        osm_familiebarnehage.save(output_filename_familiebarnehager)
    return osm, osm_familiebarnehage

def to_kommunenr(arg):
    """Allow flexible format for kommune-name, by either number or name"""
    nr2name, name2nr = kommunenummer()
    try:
        nr = int(arg)
    except ValueError:          # not int
        try:
            nr = name2nr[arg]
        except KeyError:
            raise KeyError('Kommune-name "%s" not recognized' % arg)

    if not nr in nr2name:
        raise ValueError('Kommune-nr %s not found in kommunenummer.py, feel free to correct the file' % nr)
    
    return '{0:04d}'.format(nr)

if __name__ == '__main__':
    import argparse_util
    parser = argparse_util.get_parser('''Converts norwegian kindergarten-data from 
"Utdanningdsdirektoratet Nasjonalt barnehageregister" to .osm format for import into openstreetmap. 
Specify either by --nbr_id or by --kommune.''',
                                      epilog='Example: ./barnehagefakta_osm.py --kommune ALL --update_kommune')
    parser.add_argument('--nbr_id', nargs='+', help='Unique NBR-id(s) to download and parse (e.g. 1015988).')
    parser.add_argument('--kommune', nargs='+', help='Assumes barnehageregister_nbrId.py has been called, otherwise, use with --update_kommune. Specify either kommunenummer (e.g. 0213 or 213) or kommunename (e.g. Ski). Use the special "ALL" for all kommunes. Places a .osm file in each of the kommune folders unless --output_filename is used.')
    parser.add_argument('--update_kommune', default=False, action='store_true',
                        help='Finds valid nsrIds for the given --kommunenummer (calls barnehageregister_nbrId.py)')
    parser.add_argument('--output_filename', default=None,
                        help='Specify output filename, defaults to "barnehagefakta.osm", for kommuner it will default to cache_dir/<nr>/barnehagefakta.osm')
    parser.add_argument('--cache_dir', default='data',
                        help='Specify directory for cached .json files, defaults to data/')
    argparse_util.add_verbosity(parser, default=logging.DEBUG)
    
    args = parser.parse_args()

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(args.loglevel)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    def add_file_handler(filename='warnings.log'):
        fh = logging.FileHandler(filename, mode='w')
        fh.setLevel(logging.WARNING)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        return fh
    fh = add_file_handler()

    output_filename = args.output_filename
    osm, osm_f = None, None
    
    if args.kommune:      # list of kommuner given
        if args.kommune == ['ALL']:
            nr2name, _ = kommunenummer()
            kommunenummer = map(to_kommunenr, nr2name.keys())
        else:
            kommunenummer = map(to_kommunenr, args.kommune)
        
        for kommune_id in kommunenummer:
            cache_dir = os.path.join(args.cache_dir, kommune_id) # work inside kommune folder
            logger.removeHandler(fh)
            warn_filename = os.path.join(cache_dir, 'warnings.log')
            fh = add_file_handler(file_util.create_dirname(warn_filename))
            
            if args.update_kommune:
                update_kommune(kommune_id, cache_dir=args.cache_dir)

            k = get_kommune(kommune_id, cache_dir=args.cache_dir)

            if args.output_filename is None:
                output_filename = os.path.join(cache_dir, 'barnehagefakta.osm')
                main(k, output_filename, cache_dir)
            else:
                osm, osm_f = main(k, output_filename, cache_dir, osm, osm_f,
                                  save=kommune_id == kommunenummer[-1]) # hack
                
    if args.nbr_id:
        if args.output_filename is None:
            output_filename = 'barnehagefakta.osm'
        main(args.nbr_id, output_filename, args.cache_dir)
