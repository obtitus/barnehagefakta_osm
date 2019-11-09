#!/usr/bin/env python
# -*- coding: utf8

"""Gets and parses search results from nbr.udir.no for nbrId and Eier"""
# Standard python imports
import os
import re
import json
import logging
logger = logging.getLogger('barnehagefakta.barnehageregister_nbrId')
# non-standard imports
from bs4 import BeautifulSoup
# This project
from utility_to_osm import file_util
from utility_to_osm import gentle_requests
request_session = gentle_requests.GentleRequests()

try:
    basestring
except NameError:               # python3
    basestring = str

def get(kommune_id, page_nr=1, old_age_days=30, cache_dir='data'):
    url = 'https://nbr.udir.no/sok/sokresultat?FritekstSok=&NedlagteEnheter=false&AktiveEnheter=true&AktiveEnheter=false&Eiere=false'
    url += '&Kommune.Id={0:s}'.format(kommune_id)
    url += '&Sidenummer={0:d}'.format(page_nr)

    filename = os.path.join(cache_dir, kommune_id, 'nbr_udir_no_page{0}.html'.format(page_nr))
    return request_session.get_cached(url, filename, old_age_days=old_age_days)
    
def find_search_table(soup):
    """Finds correct table, raise exception if multiple (or no) matching tables are found"""
    ret = list()
    # for table in soup.find_all('ul'):
    #     try:
    #         if 'search-result' in table['class'] or 'search-results' in table['class']:
    #             ret.append(table)
    #     except KeyError: pass
    
    smaller_soup = soup.find('section', class_='section row')
    if smaller_soup is not None:
        soup = smaller_soup

    try:
        if 'no-result' in soup.p['class']:
            return soup
    except: pass
    
    for table in soup.find_all('ul'):
        try:
            if 'search-result' in table['class'] or 'search-results' in table['class']:
                ret.append(table)
        except KeyError: pass
    

    if len(ret) == 1:
        return ret[0]
    elif len(ret) == 0:
        logger.error('soup = %s', soup.prettify())
        raise BaseException('Parsing error, no search-result tables found')        
    else:
        logger.error('soup = %s', soup.prettify())
        raise BaseException('Parsing error, multiple search-result tables found')

def get_raw(table):
    for row in table.find_all('li'):
        logger.debug('row = """%s"""', row.prettify())

        raw_data = dict()
        try:
            link, name = row.h2.a['href'], row.h2.a.text
        except AttributeError:
            logger.debug('skipping row')
            continue
        
        reg = re.match('/enhet/(eier/)?(\d+)', link)
        if reg.group(1) is not None:
            logger.warning('%s We got a "eier" when requesting Eiere=false, skipping', link)
            continue
        nbrId = reg.group(2)
        logger.info('Name = "%s" (%s)', name, nbrId)
        raw_data['name'] = name
        raw_data['nbrId'] = nbrId

        # fixme: cleaner way to find div with class='search-result-owner'
        for element in row.find_all('div'):
            if 'search-result-owner' in element['class']:
                try: element.span.text
                except Exception as e:
                    logger.exception('nbrId=%s vops element=%s, error=%s', nbrId, element, e)
                    continue
                
                if element.span.text == 'Eier':
                    link = element.div.a
                    raw_data['Eier'] = link.text

                    reg = re.match('/enhet/eier/(\d+)', link['href'])
                    eier_orgnr = reg.group(1)
                    raw_data['Eier_orgNr'] = eier_orgnr
                    #print raw_data

        # legacy: fixme remove?
        for element in row.find_all('span'):
            #print 'elem "%s"' % element.text
            split = element.text.split(':')
            if len(split) == 2:
                logger.debug('colon separated, %s', split)
                assert split[0] not in raw_data
                raw_data[split[0]] = split[1]

                if split[0] == 'Eier':
                    link = element.a['href']
                    reg = re.match('/enhet/eier/(\d+)', link)
                    eier_orgnr = reg.group(1)
                    raw_data['Eier_orgNr'] = eier_orgnr
            else:
                logger.debug('not colon separated, %s, ignoring', split)

        yield raw_data

def parse(content):
    if content is None:
        return

    # Sanity check the data
    expected_data = {'nbrId': int,
                     'name': basestring,
                     'Eier_orgNr': int,
                     'Eier': basestring,
                     'Org.Nr': int}
                     #'Type': basestring}
    ignore_data = ['Org.Nr'] # org.nummer of the barnehage (not operator!)

    soup = BeautifulSoup(content, 'lxml')
    table = find_search_table(soup)
    
    for raw_data in get_raw(table):
        if len(raw_data) != len(expected_data):
            logger.error('length %s != %s, got %s' % (len(raw_data), len(expected_data), raw_data.keys()))
            continue
        
        #assert len(raw_data) == len(expected_data), 'length %s != %s, got %s' % (len(raw_data), len(expected_data), raw_data.keys())
        #assert raw_data['Type'] == 'Bedrift' # seems to be true, so why not check for it
        for key in expected_data:
            if expected_data[key] == basestring:
                assert isinstance(raw_data[key], basestring)
                raw_data[key] = raw_data[key].strip()
            else:
                raw_data[key] = expected_data[key](raw_data[key])

        for key in ignore_data:
            del raw_data[key]
        
        yield raw_data

def all_pages(kommune_id):
    for page_nr in range(1, 1024): # max pages (Oslo currently has 832)
        content = get(kommune_id, page_nr=page_nr) # WARNING: passing page_nr=0 returns the same as page_nr=1
        data = list(parse(content))
        if len(data) == 0:      # requesting past the page number does not raise any errors, but returns an empty list
            break
        for row in data:
            yield row
    else:
        raise ValueError('ERROR, max pages exceeded, %s', page_nr)

def all_location(kommune_id, old_age_days=30, cache_dir='data'):
    """Uses the new API: http://www.barnehagefakta.no/api/Location/kommune/<kommune_id> to
    return all kindergartens in the given kommune
    FIXME: This does not include 'Eier', so we will stick to the old method of parsing nbr."""
    url = 'http://www.barnehagefakta.no/api/Location/kommune/{kommune_id}'.format(kommune_id=kommune_id)
    filename = os.path.join(cache_dir, kommune_id, 'location_kommune.json')
    # get
    content = request_session.get_cached(url, filename, old_age_days=old_age_days)
    # parse
    l = json.loads(content)
    for item in l:
        row = dict()
        # fixme: for backward-compatibility, rename:
        row['nbrId'] = item['nsrId']
        row['name'] = item['navn']
        yield row
    
def update_kommune(kommune_id, cache_dir = 'data'):
    filename_output = os.path.join(cache_dir, kommune_id, 'nbr_udir_no.json')
    file_util.create_dirname(filename_output)
    with open(filename_output, 'w') as f_out:
        for row in all_pages(kommune_id): # all_location(kommune_id): #
            f_out.write(json.dumps(row) + '\n') # FIXME: newline makes it human readable, but not json readable..
    return filename_output

def get_kommune(kommune_id, cache_dir='data'):
    """Assumes update_kommune has been called""" # fixme?
    filename_input = os.path.join(cache_dir, kommune_id, 'nbr_udir_no.json')    
    with open(filename_input, 'r') as f_out:
        for row in f_out:
            yield json.loads(row)

if __name__ == '__main__':
    import argparse_util
    parser = argparse_util.get_parser('''Gets nbr_ids for the given kommune by searching https://nbr.udir.no/sok/.
    Note: this file is called by barnehagefakta_osm.py when --update_kommune is passed.''')
    parser.add_argument('kommunenr', nargs='+',
                        help='List of kommune-ids')
    parser.add_argument('--cache_dir', default='data',
                        help='Specify directory for cached .html files and .json outputs, defaults to data/')    
    argparse_util.add_verbosity(parser, default=logging.DEBUG)

    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)
    for kommune_id in args.kommunenr:
        update_kommune(kommune_id)
