#!/usr/bin/env python
# -*- coding: utf8

# Standard python imports
import os
import re
import json
from datetime import datetime
import logging
logger = logging.getLogger('barnehagefakta.update_osm')

# Non standard
import requests
request_session = requests.session()
import osmapis
# This project
import file_util
try:
    import mypasswords
except ImportError:
    print 'No mypasswords.py file found'
    print 'Please create mypasswords.py, please see mypasswords_template.py'

from barnehagefakta_osm import create_osmtags

def find_outdated(root):
    """Yields all {nbr_id}-%Y-%m-%d-OUTDATED.json files below directory 'root'.
    the tuple (filename_outdated, filename_updated, nbr_id) is yielded
    """
    for root, dirs, files in os.walk(root):
        for f in files:
            if f.endswith('OUTDATED.json'):
                try:
                    reg = re.search('nbrId(\d+)-(\d+-\d+-\d+)-OUTDATED.json', f)
                    nbr_id = reg.group(1)
                    date = datetime.strptime(reg.group(2), '%Y-%m-%d')
                    filename_updated = f.replace('-'+reg.group(2)+'-OUTDATED', '') # hack
                    filename_updated = os.path.join(root, filename_updated)
                except Exception as e:
                    raise ValueError('Invalid OUTDATED.json filename detected, "%s/%s", %s' % (root, f, e))

                filename_outdated = os.path.join(root, f)
                yield filename_outdated, filename_updated, nbr_id
                #yield os.path.join(root, f), date, nbr_id

def find_all_nsrid_osm_elements(osm, nsrid=None):
    """Parses the given osmapis.OSM and yields all elements containing the tag barnehage:nsrid,
    the result might contain osmapis.Node, osmapis.Way or osmapis.Relation.
    Optionally only yield those with barnehage:nsrid=nsrid"""
    for elem in osm:
        #print 'elem, tags', elem.tags, 'attribs', elem.attribs
        if 'no-barnehage:nsrid' in elem.tags:
            if nsrid is not None and elem.tags['no-barnehage:nsrid'] != nsrid:
                continue
            
            logger.debug('found tags = "%s"\nattribs="%s"', elem.tags, elem.attribs)
            yield elem

def overpass_nsrid(nsrid='*',
                   bbox_scandinavia = '[bbox=3.8671874,57.63363,31.96582,71.6498329]'): 
     # bbox_scandinavia: limit request size, should contains all of Norway.

    filename = 'overpass_api_cache_%s_%s.xml' % (nsrid, bbox_scandinavia)
    filename = filename.replace(',', '')
    filename = filename.replace('*', '-')
    filename = filename.replace('[', '')
    filename = filename.replace(']', '')
    filename = filename.replace('=', '')
    logger.debug('cached overpass filename "%s"', filename)
    
    cached, outdated = file_util.cached_file(filename, old_age_days=1)
    if cached is not None and not(outdated):
        return cached
    
    r = request_session.get('http://www.overpass-api.de/api/xapi_meta?*[no-barnehage:nsrid=%s]%s' % (nsrid, bbox_scandinavia))
    ret = r.content

    if r.status_code == 200:
        file_util.write_file(filename, ret)
        return ret
    else:
        logger.error('Invalid status code %s', r.status_code)
        return None
    
def update_osm(original, modified, username=None, password=None, comment=''):
    #'''osmapis changeset example'''
    if username is None:
        username = mypasswords.osm_username
    if password is None:
        password = mypasswords.osm_password
        
    osc = osmapis.OSC.from_diff(original, modified)
    print 'DIFF:', osc
    raw_input('Please confirm (ctrl-c to cancel, enter to continue)')
    
    api = osmapis.API(username=username, password=password,
                      changeset_tags=dict(source="Nasjonalt barnehageregister",
                                          created_by="barnehagefakta_osm.py"))
    changeset = api.create_changeset(comment=comment)
    changeset_id = api.get_changeset_id(changeset)

    api.upload_diff(osc=osc, changeset=changeset)
    api.close_changeset(int(changeset_id))
    return True

def resolve_conflict(osm_element, osm_outdated, osm_updated):
    print 'outdated', osm_outdated
    print 'updated', osm_updated
    osm_element_tags_original = dict(osm_element.tags) # keep a copy
    
    if osm_outdated.attribs['lat'] != osm_updated.attribs['lat'] or\
       osm_outdated.attribs['lon'] != osm_updated.attribs['lon']:
        logger.warning('Lat/lon has changed, it is advisable to check if this is an improvement in the NBR data or if the kindergarden actually has moved')

    if osm_outdated.tags == osm_updated.tags: # all tags we care about are equal, so mark as resolved
        logger.info('All relevant tags are equal, conflict resolved.')
        return True

    # Tags added
    # Only add if it does not conflict with existing osm value.
    for key in osm_updated.tags:
        # If NBR adds additonal tags that where not present before
        if not(key in osm_outdated.tags):
            logger.info('new tag "%s"', key)
            if key in osm_element.tags: # osm already has this key
                if osm_element.tags[key] != osm_updated.tags[key]: # and there is a missmatch
                    logger.warning('Unresolved conflict, NBR has added %s="%s", but osm already has the value "%s"',
                                   key, osm_updated.tags[key], osm_element.tags[key])
                    return False
            # else:
            osm_element.tags[key] = osm_updated.tags[key]

    # Tags deleted
    for key in osm_outdated.tags:
        # If NBR has removed a key
        if not(key in osm_updated.tags):
            logger.info('removed tag "%s"', key)
            if key in osm_element.tags: # should be present in osm, else: just move on
                if osm_element.tags[key] == osm_outdated.tags[key]: # osm value corresponds to the outdated value (not tampered with)
                    logger.info('Removing tag "%s=%s"', key, osm_element.tags[key])
                    del osm_element.tags[key]
                else:           # tampered with in osm
                    logger.warning('Unresolved conflict, NBR has deleted %s="%s", but osm has changed the value to "%s"',
                                   key, osm_outdated.tags[key], osm_element.tags[key])
                    return False

    # Tags modified
    # get keys that are in both updated and outdated
    s = set(osm_updated.tags.keys())
    s.intersection_update(osm_outdated.tags.keys())
    for key in s:
        # NBR has modified a value
        if osm_updated.tags[key] != osm_outdated.tags[key]:
            if key in osm_element.tags:
                if osm_element.tags[key] != osm_outdated.tags[key]:
                    logger.warning('Unresolved conflict, NBR has modified %s="%s" to "%s", but osm has the value "%s"',
                                   key, osm_outdated.tags[key], osm_updated.tags[key], osm_element.tags[key])
                    return False
                else: # Else: osm matches the old value, i.e. not tampered with
                    logger.info('Modifying %s="%s" to "%s"', key, osm_outdated.tags[key], osm_updated.tags[key])
                    osm_element.tags[key] = osm_updated.tags[key]
                    
            else:
                logger.warning('Unresolved conflict, NBR has modified %s="%s" to "%s", but osm does not have this key',
                               key, osm_outdated.tags[key], osm_updated.tags[key])
                return False

    # fixme: Re-write, do not return False all over the place?
    
    if osm_element_tags_original != osm_element.tags:
        return 'update'
    else:
        return True

if __name__ == '__main__':
    import argparse_util
    parser = argparse_util.get_parser('Keeps OSM objects with no-barnehage:nsrid=* updated if there are changes in the NBR data. Does not overwrite modified OSM data.')
    parser.add_argument('--data_dir', default='data',
                        help='Specify directory for .osm files, defaults to data/')
    argparse_util.add_verbosity(parser, default=logging.WARNING)

    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)

    changeset_comment = 'Auto updated by barnehagefakta_osm.py. The barnehagefakta.no data has been modified and the openstreetmap data corresponds to the previous value from barnehagefakta.no, an automatic update is therefore done.'
    root = 'data'
    for filename_outdated, filename_updated, nbr_id in find_outdated(root):
        logger.info('%s: outdated = "%s", updated = "%s"', nbr_id, filename_outdated, filename_updated)
        outdated = json.load(open(filename_outdated))
        updated = json.load(open(filename_updated))
        osm_outdated, _ = create_osmtags(outdated)
        osm_updated, _ = create_osmtags(updated)

        if osm_outdated.tags == osm_updated.tags: # none of the tags that we care about has changed
            logger.info('nbrid = %s no relevant tags changed, removing', nbr_id) # fixme: check for lat/lon changes...
            os.remove(filename_outdated)
            continue

        xml = overpass_nsrid()
        # r = request_session.get('http://www.overpass-api.de/api/xapi_meta?*[no-barnehage:nsrid=%d]%s' % (int(nbr_id), bbox_scandinavia))
        # xml = r.content
        # xml = reply_way
        #print 'xml', xml

        osm_original = osmapis.OSM.from_xml(xml)        
        osm = osmapis.OSM.from_xml(xml)
        osm_elements = list(find_all_nsrid_osm_elements(osm, nsrid=nbr_id))
        if len(osm_elements) == 0:
            logger.info('nbrid = %s has not been added to osm, removing the OUTDATED file', nbr_id)
            os.remove(filename_outdated)
        elif len(osm_elements) == 1:
            osm_element = osm_elements[0]
            logger.info('resolve_conflict(osm_element=%s %s, ...)', type(osm_element), osm_element.tags)
            resolved = resolve_conflict(osm_element, osm_outdated, osm_updated)
            if resolved == 'update':
                resolved = update_osm(original=osm_original,
                                      modified=osm,
                                      comment=changeset_comment)
                
            if resolved:
                logger.info('nbrid = %s has been resolved, removing the OUTDATED file', nbr_id)
                os.remove(filename_outdated)
        else:
            logger.error('OSM contains multiple nodes/ways/relations with the tag no-barnehage:nsrid=%s, please fix this.', nbr_id)
            for ix, e in enumerate(osm_elements):
                print 'DUPLICATE %d: %s\n"%s"' % (ix, e.tags, e)
            exit(1)
