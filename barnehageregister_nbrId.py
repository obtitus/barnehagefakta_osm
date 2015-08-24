"""Gets and parses search results from nbr.udir.no for nbrId and Eier"""
# Standard python imports
import os
import re
import json
import logging
logger = logging.getLogger('barnehagefakta.nbrId')
# non-standard imports
import requests
request_session = requests.session()
from bs4 import BeautifulSoup
# This project
import file_util

def get(kommune_id, page_nr=1, old_age_days=30, cache_dir='data'):
    url = 'https://nbr.udir.no/sok/sokresultat?FritekstSok=&NedlagteEnheter=false&AktiveEnheter=true&AktiveEnheter=false&Eiere=false'
    url += '&Kommune.Id={0:s}'.format(kommune_id)
    url += '&Sidenummer={0:d}'.format(page_nr)

    filename = os.path.join(cache_dir, kommune_id, 'nbr_udir_no_kommune{0}-page{1}.html'.format(kommune_id, page_nr))
    cached = file_util.cached_file(filename, old_age_days)
    if cached is not None:
        return cached

    try:
        r = request_session.get(url)
    except requests.ConnectionError as e:
        logger.error('Could not connect to %s, try again later? %s', url, e)
        return None
    
    logger.info('requeted %s, got %s', url, r)
    if r.status_code == 200:
        ret = r.content
        file_util.write_file(filename, ret)
        return ret
    else:
        logger.error('Invalid status code %s', r.status_code)
        return None

def find_search_table(soup):
    """Finds correct table, raise exception if multiple (or no) matching tables are found"""
    ret = list()
    for table in soup.find_all('ul'):
        if 'search-result' in table['class']:
            ret.append(table)

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
        link, name = row.h2.a['href'], row.h2.a.text
        reg = re.match('/enhet/(\d+)', link)
        nbrId = reg.group(1)
        logger.info('Name = "%s" (%s)', name, nbrId)
        raw_data['name'] = name
        raw_data['nbrId'] = nbrId

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
    # Sanity check the data
    expected_data = {'nbrId': int,
                     'name': basestring,
                     'Eier_orgNr': int,
                     'Eier': basestring,
                     'Org.nummer': int,
                     'Type': basestring}
    ignore_data = ['Org.nummer', # org.nummer of the barnehage (not operator!)
                   'Type']

    soup = BeautifulSoup(content)
    table = find_search_table(soup)
    
    for raw_data in get_raw(table):
        assert len(raw_data) == len(expected_data), 'length %s != %s, got %s' % (len(raw_data), len(expected_data), raw_data.keys())
        assert raw_data['Type'] == 'Bedrift' # seems to be true, so why not check for it
        for key in expected_data:
            if expected_data[key] == basestring:
                assert isinstance(raw_data[key], basestring)
                raw_data[key] = raw_data[key].strip()
            else:
                raw_data[key] = expected_data[key](raw_data[key])

        for key in ignore_data:
            del raw_data[key]
        
        yield raw_data
        
if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.DEBUG)
    kommune_id = sys.argv[1]

    cache_dir = 'data'
    filename_output = os.path.join(cache_dir, kommune_id, 'nbr_udir_no.json')
    f_out = open(filename_output, 'w')
    
    for page_nr in xrange(1, 1024): # max pages (Oslo currently has 832)
        content = get(kommune_id, page_nr=page_nr) # NOTE: passing page_nr=0 returns the same as page_nr=1
        data = list(parse(content))
        if len(data) == 0:      # requesting past the page number does not raise any errors, but returns an empty list
            break
        for row in data:
            f_out.write(json.dumps(row) + '\n')
    else:
        raise ValueError('ERROR, max pages exceeded, %s', page_nr)
        
    f_out.close()
