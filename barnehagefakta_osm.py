# Standard python imports
import re
import logging
logger = logging.getLogger('barnehagefakta')
# Non standard
import osmapis
# This project:
from barnehagefakta_get import barnehagefakta_get

osmobj = osmapis.OSM()

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

    # Note: No operator is given for 'privat' barnehage        
    operator = ''
    if not(udir_tags['erPrivatBarnehage']):
        operator = udir_tags['kommune']['kommunenavn'] + ' ' + 'kommune' # can I always add this?

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
            'fee': udir_tags['kostpenger'] != 0,
            'operator':operator,
            'min_age':min_age,
            'max_age':max_age}

    # cleanup
    remove_empty_values(tags)
    values_to_str(tags)

    # Create and return osmapis.Node
    node = osmapis.Node(attribs=attribs, tags=tags)
    logger.info('Created node %s', node)
    return node

def main(lst):
    osm = osmapis.OSM()
    for nbr_id in lst:
        udir_tags = barnehagefakta_get(nbr_id)
        node = create_osmtags(udir_tags)
        osm.add(node)
    osm.save('barnehagefakta.osm')
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # fixme: print usage
    import sys
    nbr_ids = sys.argv[1:]
    main(nbr_ids)
