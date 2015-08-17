# Standard python imports
import os
import json
import time
import pprint
pretty_printer = pprint.PrettyPrinter()
import logging
logger = logging.getLogger('barnehagefakta.get')
# Non-standard imports
import requests
request_session = requests.session()

# Utility file functions:
def read_file(filename):
    with open(filename, 'r') as f:
        return f.read()
def write_file(filename, content):
    """Write content to filename, tries to create dirname if the folder does not exist."""
    dirname = os.path.dirname(filename)
    if not(os.path.exists(dirname)):
        os.mkdir(dirname)
    
    with open(filename, 'w') as f:
        return f.write(content)

def fileAge(filename):
    fileChanged = os.path.getmtime(filename)
    now = time.time()
    age = (now - fileChanged)/(60*60*24) # age of file in days
    return age

#
# Main
# 
def barnehagefakta_get_json(nbr_id, old_age_days=30, cache_dir='data'):
    """Returns json string for the given nbr_id, caches result to file in directory cache_dir. 
    If the cached result is older than old_age_days a new version is fetched."""
    filename = os.path.join(cache_dir, str(nbr_id) + '.json')
    if os.path.exists(filename):
        age = fileAge(filename)
        if age < old_age_days:
            return read_file(filename)
    # else, else:

    url = 'http://barnehagefakta.no/api/barnehage/{0}'.format(nbr_id)
    try:
        r = request_session.get(url)
    except requests.ConnectionError as e:
        logger.error('Could not connect to %s, try again later? %s', url, e)
        return None
    
    logger.info('requeted %s, got %s', url, r)
    ret = None
    if r.status_code == 200:
        ret = r.content
    elif r.status_code == 404:
        ret = '404'
        
    if ret is not None:
        write_file(filename, ret)
    return ret

def barnehagefakta_get(nbr_id, *args, **kwargs):
    """Returns dictionary with data for the given nbr_id. 
    Additonal arguments are passed to barnehagefakta_get_json"""
    j = barnehagefakta_get_json(nbr_id, *args, **kwargs)
    if j is None:
        return {}
    elif j == '404':
        logger.warning('nbr_id=%s returned 404', nbr_id)
        return {}
    
    dct = json.loads(j)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('barnehagefakta_get(%s) -> %s', nbr_id, pretty_printer.pformat(dct))
    return dct

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Helper script for requesting (with local cache) and parsing json data from "Utdanningdsdirektoratet Nasjonalt barnehageregister"')
    parser.add_argument('nbr_id', nargs='+', help='barnehagens unike id fra Nasjonalt barnehageregister.')
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

    for nbr_id in args.nbr_id:
        barnehagefakta_get(nbr_id, cache_dir=args.cache_dir)
    
