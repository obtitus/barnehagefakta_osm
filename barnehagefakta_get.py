# Standard python imports
import os
import json
import time
import logging
logger = logging.getLogger('barnehagefakta.get')
# Non-standard imports
import requests

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
    r = requests.get('http://barnehagefakta.no/api/barnehage/{0}'.format(nbr_id))
    logger.info('r = %s', r)
    ret = r.content
    write_file(filename, ret)
    return ret

def barnehagefakta_get(nbr_id, *args, **kwargs):
    """Returns dictionary with data for the given nbr_id. 
    Additonal arguments are passed to barnehagefakta_get_json"""
    j = barnehagefakta_get_json(nbr_id, *args, **kwargs)
    return json.loads(j)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # fixme: print usage
    import sys
    for nbr_id in sys.argv[1:]:
        barnehagefakta_get(nbr_id)
    
