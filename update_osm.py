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
# import requests
# request_session = requests.session()
try:
    import datadiff
except ImportError:
    logger.warning('no datadiff found, no pretty dictionary diff for you.')
    datadiff = None

#
import utility_to_osm.gentle_requests as gentle_requests
import utility_to_osm.file_util as file_util
    
# This project
request_session = gentle_requests.GentleRequests()
import osmapis_nsrid as osmapis
try:
    import mypasswords
except ImportError:
    print('No mypasswords.py file found')
    print('Please create mypasswords.py, please see mypasswords_template.py')

from barnehagefakta_osm import create_osmtags

def compare_capacity(value1_str, value2_str):
    '''
    There is an insane number of small updates to the capacity key, 
    this ensures we ignore any changes less than +- 10
    '''
    try:
        value1, value2 = int(value1_str), int(value2_str)
    except Exception as e: # guess these are not an integers?
        return value1 == value2
    # else:
    return abs(value1 - value2) < 10


def get_osm_files(folder):
    """Yields parsed .osm files below folder as a tuple (filename, osmapis.OSMnsrid)"""
    for filename in os.listdir(folder):
        filename = os.path.join(folder, filename)
        if filename.endswith('.osm'):
            logger.info('.osm file %s', filename)
            with open(filename) as f:
                data = osmapis.OSMnsrid.from_xml(f.read())
            
            yield filename, data

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
        #print('elem, tags', elem.tags, 'attribs', elem.attribs)
        if 'no-barnehage:nsrid' in elem.tags:
            if nsrid is not None and elem.tags['no-barnehage:nsrid'] != nsrid:
                continue
            
            logger.debug('found tags = "%s"\nattribs="%s"', elem.tags, elem.attribs)
            yield elem

def overpass_nsrid(nsrid='*',
                   bbox_scandinavia = '[bbox=3.33984375,57.468589192089325,38.408203125,81.1203884020757]'):
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
    
def update_osm(original, modified, username=None, password=None, comment='', osm_element=None):
    #'''osmapis changeset example'''
    if username is None:
        username = mypasswords.osm_username
    if password is None:
        password = mypasswords.osm_password
        
    osc = osmapis.OSC.from_diff(original, modified)
    print('DIFF: %s' % osc)
    user_input = raw_input('Please confirm, enter to continue, "s" or "n" to skip, "d" to delete>>[y] ').lower()
    if user_input in ('y', ''):
        update = True
    elif user_input in ('s', 'n'):
        print('Skipping.')
        return False
    elif user_input in ('d', 'delete'):
        print('Deleting')
        return True
    elif user_input in ('q', 'e'):
        exit(1)
    elif user_input in ('ow', 'open website'):
        import webbrowser
        webbrowser.open(osm_element.tags['contact:website'])
        return update_osm(original, modified,
                          username=username, password=password, comment=comment,
                          osm_element=osm_element)
    else:
        print('unkown user_input, breaking.', repr(user_input))
        exit(1)

    
    api = osmapis.API(username=username, password=password,
                      changeset_tags=dict(source="Nasjonalt barnehageregister",
                                          created_by="barnehagefakta_osm.py"))
    changeset = api.create_changeset(comment=comment)
    changeset_id = api.get_changeset_id(changeset)

    api.upload_diff(osc=osc, changeset=changeset)
    api.close_changeset(int(changeset_id))
    return True

def resolve_conflict(osm_element, osm_outdated, osm_updated):
    keys_to_ignore = ('ADDRESS', )
    
    logger.debug('resolve_conflict:osm: %s', osm_element)    
    logger.debug('resolve_conflict:outdated: %s', osm_outdated)
    logger.debug('resolve_conflict:updated: %s', osm_updated)
    
    osm_element_tags_original = dict(osm_element.tags) # keep a copy
    
    if osm_outdated.attribs['lat'] != osm_updated.attribs['lat'] or\
       osm_outdated.attribs['lon'] != osm_updated.attribs['lon']:
        logger.warning('Lat/lon has changed, it is advisable to check if this is an improvement in the NBR data or if the kindergarden actually has moved')
    try:
        if osm_outdated.tags['doNotImportAddress'] != osm_updated.tags['doNotImportAddress']:
            logger.warning('Address has changed, it is advisable to check if this is an improvement in the NBR data or if the kindergarden actually has moved')
            osm_outdated.tags['doNotImportAddress'] = osm_updated.tags['doNotImportAddress']
    except KeyError:
        pass

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
    ignored_capacity_change = False
    for key in s:
        # NBR has modified a value
        if osm_updated.tags[key] != osm_outdated.tags[key]:
            logger.info('modified tag "%s"', key)
            if key in osm_element.tags:
                if osm_element.tags[key] == osm_updated.tags[key]:
                    logger.info('NBR has modified %s="%s" to "%s", but osm already has the value "%s"',
                                   key, osm_outdated.tags[key], osm_updated.tags[key], osm_element.tags[key])
                    #osm_element.tags[key] = osm_updated.tags[key]
                    continue
                if osm_element.tags[key] != osm_outdated.tags[key]:
                    logger.warning('Unresolved conflict, NBR has modified %s="%s" to "%s", but osm has the value "%s"',
                                   key, osm_outdated.tags[key], osm_updated.tags[key], osm_element.tags[key])
                    #osm_element.tags[key] = osm_updated.tags[key]
                    return False
                else: # Else: osm matches the old value, i.e. not tampered with
                    # Check for small changes in capacity (i.e. don't care)
                    if key == 'capacity' and compare_capacity(osm_outdated.tags[key], osm_updated.tags[key]):
                        logger.info('Ignoring small capacity change %s=%s to %s', key, osm_outdated.tags[key], osm_updated.tags[key])
                        ignored_capacity_change = True # This moves: osm_element.tags[key] = osm_updated.tags[key], to only happen if we are actually doing an update
                        continue
                        
                    logger.info('Modifying %s="%s" to "%s"', key, osm_outdated.tags[key], osm_updated.tags[key])
                    osm_element.tags[key] = osm_updated.tags[key]
            elif key in keys_to_ignore:
                logger.info('%s changed, ignoring. %s to %s' % (key, osm_outdated.tags[key], osm_updated.tags[key]))
                continue
            else:
                logger.warning('Unresolved conflict, NBR has modified %s="%s" to "%s", but osm does not have this key',
                               key, osm_outdated.tags[key], osm_updated.tags[key])
                #osm_element.tags[key] = osm_updated.tags[key]
                return False

    # fixme: Re-write, do not return False all over the place?
    
    if osm_element_tags_original != osm_element.tags:
        if ignored_capacity_change:
            osm_element.tags['capacity'] = osm_updated.tags['capacity']
        return 'update'
    else:
        return True

if __name__ == '__main__':
    import utility_to_osm.argparse_util as argparse_util
    parser = argparse_util.get_parser('Keeps OSM objects with no-barnehage:nsrid=* updated if there are changes in the NBR data. Does not overwrite modified OSM data.')
    parser.add_argument('--data_dir', default='data',
                        help='Specify directory for .osm files, defaults to data/')
    parser.add_argument('--batch', default=False, action='store_true',
                        help='Do not promt for user input (will not update OSM, run without --batch to clear all conflicts)')
    parser.add_argument('--log_filename', default='update_osm.log',
                         help='log file for all logging levels, defaults to update_osm.log.')
    argparse_util.add_verbosity(parser, default=logging.WARNING)

    args = parser.parse_args()

    #logging.basicConfig(level=args.loglevel)
    # logger_adapter_dict = dict(nbr_id=None)
    # main_logger = logging.LoggerAdapter(main_logger, logger_adapter_dict)    
    
    main_logger = logging.getLogger('barnehagefakta')
    main_logger.setLevel(logging.DEBUG)
    # create console handler with a custom log level
    ch = logging.StreamHandler()
    ch.setLevel(args.loglevel)
    main_logger.addHandler(ch)
    
    # create file handler which logs even info messages
    fh = logging.FileHandler(args.log_filename)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    main_logger.addHandler(fh)

    changeset_comment = 'Auto updated by barnehagefakta_osm.py. The barnehagefakta.no data has been modified and the openstreetmap data corresponds to the previous value from barnehagefakta.no, an automatic update is therefore done.'
    root = args.data_dir


    # Summary counters
    N_outdated = 0              # total
    N_404 = 0                   # was 404
    N_no_relevant_tags = 0      # no osm relevant tags have changed
    N_not_added = 0             # not added to osm
    N_need_update = 0
    N_resolved = 0
    N_unresolved = 0
    for filename_outdated, filename_updated, nbr_id in find_outdated(root):
        #logger_adapter_dict['nbr_id'] = nbr_id
        N_outdated += 1
        logger.info('%s: outdated = "%s", updated = "%s"', nbr_id, filename_outdated, filename_updated)
        outdated = json.load(open(filename_outdated))
        updated = json.load(open(filename_updated))

        xml = overpass_nsrid()
        osm_original = osmapis.OSMnsrid.from_xml(xml)
        osm = osmapis.OSMnsrid.from_xml(xml)
        osm_elements = osm.nsrids.get(nbr_id, [])

        if outdated == 404:
            N_404 += 1
            logger.info('nbrid = %s was 404, removing', nbr_id)
            os.remove(filename_outdated)
            continue
        if updated == 404:
            if len(osm_elements) == 0:
                logger.warning('nbrid = %s is now 404, previous = %s is not imported to osm, ignoring', nbr_id, outdated)
                os.remove(filename_outdated)
            else:
                logger.error('ERROR: nbrid = %s is now 404. FIXME: support this, previous = %s', nbr_id, outdated)
                # Note: do not delete before we have a good fix for this!
            
            continue
        
        osm_outdated, _ = create_osmtags(outdated, cache_dir=args.data_dir)
        osm_updated, _ = create_osmtags(updated, cache_dir=args.data_dir)

        if osm_outdated.tags == osm_updated.tags: # none of the tags that we care about has changed
            N_no_relevant_tags += 1
            logger.info('nbrid = %s no relevant tags changed, removing', nbr_id) # fixme: check for lat/lon changes...
            if datadiff is not None:
                logger.debug("%s", datadiff.diff(outdated, updated))
                
            os.remove(filename_outdated)
            continue

        if len(osm_elements) == 0:
            N_not_added += 1
            logger.info('nbrid = %s has not been added to osm, removing the OUTDATED file', nbr_id)
            if datadiff is not None:
                logger.info("%s", datadiff.diff(outdated, updated))
            
            os.remove(filename_outdated)
        elif len(osm_elements) == 1:
            osm_element = osm_elements[0]
            logger.info('resolve_conflict(osm_element=%s %s, ...)', type(osm_element), osm_element.tags)
            resolved = resolve_conflict(osm_element, osm_outdated, osm_updated)
            if resolved == False:
                N_unresolved += 1
            elif resolved == 'update':
                if args.batch is False:
                    resolved = update_osm(original=osm_original,
                                          modified=osm,
                                          comment=changeset_comment,
                                          osm_element=osm_element)
                else:
                    logger.warning('Run without --batch to update osm')
                    N_need_update += 1

            if resolved == True:
                N_resolved += 1
                logger.info('nbrid = %s has been resolved, removing the OUTDATED file', nbr_id)
                os.remove(filename_outdated)
        else:
            logger.error('OSM contains multiple nodes/ways/relations with the tag no-barnehage:nsrid=%s, please fix this.', nbr_id)
            for ix, e in enumerate(osm_elements):
                print('DUPLICATE %d: %s\n"%s"' % (ix, e.tags, e))
            exit(1)

    # Summary
    resolved = N_404 + N_no_relevant_tags + N_not_added + N_resolved
    summary = ''
    if N_404 != 0:
        summary += '%s was 404, ' % N_404
    if N_no_relevant_tags != 0:
        summary += '%s non-relevant tag changes, ' % N_no_relevant_tags
    if N_not_added != 0:
        summary += '%s not added to OSM ' % N_not_added
    if N_resolved != 0:
        summary += '%s was resolved. ' % N_resolved
    if N_need_update != 0:
        summary += '%s need to run without --batch ' % N_need_update
    if N_unresolved != 0:
        summary += '%s need manual fixing ' % N_unresolved
    logger.info('Done. %s outdated, Resolved: %s/%s. %s', N_outdated, resolved, N_outdated, summary)
