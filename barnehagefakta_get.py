#!/usr/bin/env python
# Standard python imports
import os
import json
from datetime import datetime
import pprint
pretty_printer = pprint.PrettyPrinter()
import logging
logger = logging.getLogger('barnehagefakta.get')
# Non-standard imports
import requests
# This project
import gentle_requests
request_session = gentle_requests.GentleRequests()
import file_util
#
# Main
#

def equal_json_responses(res1, res2, ignore=('id', 'indikatorDataKommune')):
    """Equivalent to res1 != res2 except that keys in 'ignore' are not compared,
    assumes equal number of keys, else returns False"""
    try:
        dct1 = json.loads(res1)
        dct2 = json.loads(res2)
        if len(dct1) != len(dct2): return False
        for key in dct1:
            if key not in dct2: return False
            if key not in ignore and dct1[key] != dct2[key]:
                return False

        logger.info('Ignoring %s, no missmatch was found', ignore)
        return True
    except:
        return res1 != res2
        
def barnehagefakta_get_json(nbr_id, old_age_days=20, cache_dir='data', keep_history=True):
    """Returns json string for the given nbr_id, caches result to file in directory cache_dir. 
    If the cached result is older than old_age_days a new version is fetched.
    By default (if keep_history is True) changes in the response will detected 
    and archived for further processing. 

    In other words:
    (1) The first time this is called, barnehagefakta.no/api/barnehage/{nbr_id} is visited, 
    the response is stored in cache_dir/barnehagefakta_no_nbrId{nbr_id}.json, 
    the file may consist of only the string '404' if the request returned 404.
    (2a) Calling the function again with the same {nbr_id} within old_age_days, 
    will simply return the content of the previously stored file
    (2b) Calling the function again with the same {nbr_id} after old_age_days has passed,
    will visit barnehagefakta again, refreshing and returning the local .json file.
    If the responce has changed from last time, the previous result is archived as
    cache_dir/barnehagefakta_no_nbrId{nbr_id}-{%Y-%m-%d}-OUTDATED.json"""
    
    filename = os.path.join(cache_dir, 'barnehagefakta_no_nbrId{0}.json'.format(nbr_id))
    cached, outdated = file_util.cached_file(filename, old_age_days)
    if cached is not None and not(outdated):
        return cached
    # else, else:

    url = 'http://barnehagefakta.no/api/barnehage/{0}'.format(nbr_id)
    try:
        r = request_session.get(url)
    except requests.ConnectionError as e:
        logger.error('Could not connect to %s, try again later? %s', url, e)
        return None
    
    logger.info('requested %s, got %s', url, r)
    ret = None
    if r.status_code == 200:
        ret = r.content
    elif r.status_code == 404:
        ret = '404'
    else:
        logger.error('Unknown status code %s', r.status_code)
        
    if ret is not None:
        if keep_history and cached is not None and not(equal_json_responses(ret, cached)): # avoid overriding previous cache
            d = datetime.utcnow()
            # note: the date will represent the date we discovered this to be outdated
            # which is not all that logical, but we just need a unique filename (assuming old_age_days > 1).
            logger.warning('Change in response for id=%s, archiving old result', nbr_id)
            file_util.rename_file(filename, d.strftime("-%Y-%m-%d-OUTDATED")) # move old one
            #return ret, cached

        file_util.write_file(filename, ret) # write
    
    return ret

class NotFoundException(Exception):
    pass

def barnehagefakta_get(nbr_id, *args, **kwargs):
    """Returns dictionary with data for the given nbr_id. 
    Additonal arguments are passed to barnehagefakta_get_json"""
    j = barnehagefakta_get_json(nbr_id, *args, **kwargs)
    if j is None:
        return {}
    elif j == '404':
        raise NotFoundException('nbr_id={0} returned 404'.format(nbr_id))
    #return {}
    
    dct = json.loads(j)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('barnehagefakta_get(%s) -> %s', nbr_id, pretty_printer.pformat(dct))
    return dct

if __name__ == '__main__':
    import argparse_util
    parser = argparse_util.get_parser('Helper script for requesting (with local cache) and parsing json data from "Utdanningdsdirektoratet Nasjonalt barnehageregister (NBR)"')
    parser.add_argument('nbr_id', nargs='+', help='Unique NBR-id(s) to download (e.g. 1015988).')
    parser.add_argument('--cache_dir', default='data',
                        help='Specify directory for cached .json files, defaults to data/')
    argparse_util.add_verbosity(parser, default=logging.DEBUG)
    
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)    

    if args.nbr_id:             # list of ids given
        for nbr_id in args.nbr_id:
            print 'Getting', nbr_id
            barnehagefakta_get(nbr_id, cache_dir=args.cache_dir)

