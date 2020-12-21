#!/usr/bin/env python
# Standard python imports
import os
import time
import json
from datetime import datetime
import pprint
pretty_printer = pprint.PrettyPrinter()
import logging
logger = logging.getLogger('barnehagefakta.get')
# Non-standard imports
import requests
# This project
from utility_to_osm import gentle_requests
request_session = gentle_requests.GentleRequests()
from utility_to_osm import file_util
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
        
def barnehagefakta_get_json(orgnr, old_age_days=5, cache_dir='data', keep_history=True):
    """Returns json string for the given orgnr, caches result to file in directory cache_dir. 
    If the cached result is older than old_age_days a new version is fetched.
    By default (if keep_history is True) changes in the response will detected 
    and archived for further processing. 

    In other words:
    (1) The first time this is called, barnehagefakta.no/api/barnehage/{orgnr} is visited, 
    the response is stored in cache_dir/barnehagefakta_no_nbrId{orgnr}.json, 
    the file may consist of only the string '404' if the request returned 404.
    (2a) Calling the function again with the same {orgnr} within old_age_days, 
    will simply return the content of the previously stored file
    (2b) Calling the function again with the same {orgnr} after old_age_days has passed,
    will visit barnehagefakta again, refreshing and returning the local .json file.
    If the responce has changed from last time, the previous result is archived as
    cache_dir/barnehagefakta_no_nbrId{orgnr}-{%Y-%m-%d}-OUTDATED.json

    May raise requests.ConnectionError if the connection fails.
    """
    
    filename = os.path.join(cache_dir, 'barnehagefakta_no_orgnr{0}.json'.format(orgnr))
    cached, outdated = file_util.cached_file(filename, old_age_days)
    if cached is not None and not(outdated):
        return cached
    # else, else:

    url = 'http://barnehagefakta.no/api/barnehage/{0}'.format(orgnr)
    # try:
    r = request_session.get(url)
    # except requests.ConnectionError as e:
    #     logger.error('Could not connect to %s, try again later? %s', url, e)
    #     return None
    
    logger.info('requested %s, got %s', url, r)
    ret = None
    if r.status_code == 200:
        ret = r.content
    elif r.status_code == 404:
        # 404 seems to occur very frequently, try again and ensure we still get 404
        time.sleep(1)
        r = request_session.get(url)
        if r.status_code != 404:
            logger.error('Seeing sporadic 404,%s for url = %s', r.status_code, url)
            if r.status_code == 200:
                ret = r.content # I guess we are OK after all...
        else:
            ret = '404'
    else:
        logger.error('Unknown status code %s', r.status_code)
        
    if ret is not None:
        if keep_history and cached is not None and not(equal_json_responses(ret, cached)): # avoid overriding previous cache
            d = datetime.utcnow()
            # note: the date will represent the date we discovered this to be outdated
            # which is not all that logical, but we just need a unique filename (assuming old_age_days > 1).
            logger.warning('Change in response for id=%s, archiving old result', orgnr)
            file_util.rename_file(filename, d.strftime("-%Y-%m-%d-OUTDATED")) # move old one
            #return ret, cached

        file_util.write_file(filename, ret) # write
    
    return ret

class NotFoundException(Exception):
    pass

def barnehagefakta_get(orgnr, *args, **kwargs):
    """Returns dictionary with data for the given orgnr. 
    Additonal arguments are passed to barnehagefakta_get_json"""
    j = barnehagefakta_get_json(orgnr, *args, **kwargs)
    if j is None:
        return {}
    elif j == '404':
        raise NotFoundException('orgnr={0} returned 404'.format(orgnr))
    #return {}
    
    dct = json.loads(j)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('barnehagefakta_get(%s) -> %s', orgnr, pretty_printer.pformat(dct))
    return dct

if __name__ == '__main__':
    from utility_to_osm import argparse_util
    
    parser = argparse_util.get_parser('Helper script for requesting (with local cache) and parsing json data from "Utdanningdsdirektoratet Nasjonalt barnehageregister (NBR)"')
    parser.add_argument('orgnr', nargs='+', help='Unique NBR-id(s) to download (e.g. 1015988).')
    parser.add_argument('--cache_dir', default='data',
                        help='Specify directory for cached .json files, defaults to data/')
    argparse_util.add_verbosity(parser, default=logging.DEBUG)
    
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)    

    if args.orgnr:             # list of ids given
        for orgnr in args.orgnr:
            print('Getting', orgnr)
            barnehagefakta_get(orgnr, cache_dir=args.cache_dir)

