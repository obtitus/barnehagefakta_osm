#!/usr/bin/env python
# -*- coding: utf8

# Standard python imports
import re
import os
import hashlib
import logging
logger = logging.getLogger('barnehagefakta.conflate_osm')
# Scientific python
import numpy as np

# This project
import file_util
import osmapis_nsrid as osmapis
from barnehagefakta_osm import to_kommunenr

def overpass_xml(xml, old_age_days=7, conflate_cache_filename=None):
    ''' Query the OverpassAPI with the given xml query, cache result for old_age_days days
    in file conflate_cache_filename (defaults to conflate_cache_<md5(xml)>.osm)
    '''
    if conflate_cache_filename is None:
        filename = 'conflate_cache_' + hashlib.md5(xml).hexdigest() + '.osm'
    else:
        filename = conflate_cache_filename
    
    cached, outdated = file_util.cached_file(filename, old_age_days=old_age_days)
    if cached is not None and not(outdated):
        print 'Using overpass responce stored as "%s". Delete this file if you want an updated version' % filename
        return osmapis.OSMnsrid.from_xml(cached)

    o = osmapis.OverpassAPI()
    osm = o.interpreter(query)

    print 'Overpass responce stored as %s' % filename
    osm.save(filename)

    return osm

def get_kommune_local(kommune):
    for root, dirs, files in os.walk('.'): # fixme
        if kommune in dirs:
            filename1 = os.path.join(root, kommune, 'barnehagefakta.osm')
            filename2 = os.path.join(root, kommune, 'barnehagefakta_familiebarnehager.osm')
            if os.path.exists(filename2):
                logger.info('Found %s', filename2)
                yield filename2
            if os.path.exists(filename1):
                logger.info('Found %s', filename1)
                yield filename1
                break
    else:
        raise BaseException("Could not find barnehagefakta.osm")

def get_kommune(kommune):
    kommune = to_kommunenr(kommune) # now a nicely formatted string e.g. '0213'
    try:
        return list(get_kommune_local(kommune))
    except BaseException:
        # urllib.request.urlretrieve('http://obtitus.github.io/barnehagefakta_osm_data/data/%s/%s', kommune, 'barnehagefakta.osm')
        # urllib.request.urlretrieve('http://obtitus.github.io/barnehagefakta_osm_data/data/%s/%s', kommune, 'barnehagefakta_familiebarnehager.osm')
        fixme_download

def score_similarity_strings(nbr_name, overpass_name):
    """Given two strings, give a score for their similarity
    100 for match and +10 for each matching word"""
    # fixme: there are a number of good python tools for looking at similar strings
    # use one! This will not catch spelling errors.
    if nbr_name is None or overpass_name is None:
        return 0
    if nbr_name == overpass_name:
        return 100
    score = 0
    for word in nbr_name.split():
        if word in overpass_name:
            score += 10
        
    return score

def score(nbr_node, overpass_element, overpass_osm):
    """Takes the two elements to compare
    nbr_node, overpass_element
    and the entire overpass_osm object to look up lat/lon for ways/relations"""
    nbr_tags = nbr_node.tags
    overpass_tags = overpass_element.tags
    score = 0    
    # how many of the keys overlapp (+1 for each)
    nbr_keys = set(nbr_tags.keys())
    overpass_keys = set(overpass_tags.keys())
    overlapp_keys = nbr_keys.intersection(overpass_keys)
    score += len(overlapp_keys)*1
    # do any of the values match (+10 for each)
    for key in overlapp_keys:
        if nbr_tags[key] == overpass_tags[key]:
            score += 10
    # are the names similar
    score += score_similarity_strings(nbr_tags.get('name', None), overpass_tags.get('name', None))
    score += score_similarity_strings(nbr_tags.get('name', None), overpass_tags.get('name:no', None))
    # same nsrid?
    try:
        if nbr_tags['no-barnehage:nsrid'] == overpass_tags['no-barnehage:nsrid']:
            score += 100
        else:
            score -= 10
    except KeyError:
        pass                    # one or more is missing no-barnehage:nsrid
        
    # how close is the lat/lon
    from generate_html import get_lat_lon # fixme, move this piece of code
    
    overpass_lat, overpass_lon = get_lat_lon(overpass_osm, overpass_element) # fixme, only returns 1 node
    nbr_lat, nbr_lon = nbr_node.attribs['lat'], nbr_node.attribs['lon']
    diff = (overpass_lat - nbr_lat)**2 + (overpass_lon - nbr_lon)**2 # no unit in particular...
    score += int(diff*1000)     # random weight...
    
    return score

def is_perfect_match(dict_a, dict_b):
    """A perfect match is in this case that all keys in a match those in b"""
    for key in dict_a:
        try:
            if dict_a[key] != dict_b[key]:
                return False
        except KeyError:
            return False
    # no breaks
    return True

def conflate(nbr_osm, overpass_osm, output_filename='out.osm'):
    output_osm = osmapis.OSMnsrid()

    # score_list = dict()
    # all_scores = list()
    nbr_elements = list(nbr_osm)
    overpass_elements = [o for o in overpass_osm if len(o.tags) != 0] # the overpass elements that actually has tags
    score_matrix = np.zeros((len(nbr_elements), len(overpass_elements)), dtype=np.int)
    logger.debug('nbr_elements = %s, %s', len(nbr_elements), nbr_elements)
    logger.debug('overpass_elements = %s, %s', len(overpass_elements), overpass_elements)

    for ix in xrange(len(nbr_elements)):
        for jx in xrange(len(overpass_elements)):
            score_matrix[ix, jx] = score(nbr_elements[ix], overpass_elements[jx],
                                         overpass_osm=overpass_osm)
        logger.debug('score for nsrid=%s, max=%s, %s %s',
                     nbr_elements[ix].tags['no-barnehage:nsrid'],
                     max(score_matrix[ix, :]),
                     len(score_matrix[ix, :]),
                     list(score_matrix[ix, :]))

    non_zero = score_matrix[np.where(score_matrix > 0)] # non-zero and non-negative (flattend)
    quantile = np.percentile(non_zero, 90)
    print 'Ignoring anything with a score lower than', quantile
    score_matrix[np.where(score_matrix < 90)] = 0

    counter = len(nbr_elements) # avoid infinite loop counter
    
    while np.nanmax(score_matrix.flatten()) > quantile and counter != 0:
        # Start with the nbr node with the highest scoring match
        m = np.nanmax(score_matrix, axis=1)
        ix_sort = np.argsort(m)
        ix = ix_sort[-1]
        nbr_element = nbr_elements[ix]
        # Go trough all potensial matches, starting with the most likely.
        jx_sort = list(np.argsort(score_matrix[ix, :]))
        jx_sort.reverse()
        for jx in jx_sort:
            overpass_element = overpass_elements[jx]
            s = score_matrix[ix, jx]
            if s == 0:
                continue
            
            if is_perfect_match(nbr_element.tags, overpass_element.tags):
                print 'Found perfect match between %s and %s, score: (%s) continuing' % (nbr_element, overpass_element, s)
                break

            head = 'Found possible match for nsrid %s, "%s" == "%s"?' % (nbr_element.tags['no-barnehage:nsrid'],
                                                                         nbr_element.tags.get('name', None),
                                                                         overpass_element.tags.get('name', None))
            print '='*5 + head + '='*5
                                                                            
            print 'Max score: (%s). Is nbr="""\n%s""", the same kindargarten as osm="""\n%s"""?' % (s,
                                                                                                   nbr_element,
                                                                                                   overpass_element)
            raw_input("")
            #break
        else: # no breaks
            print 'No likely match found for nbrid=%s' % nbr_element.tags['no-barnehage:nsrid']
            ix = None

        # Prepare for next loop:
        if ix is not None:
            score_matrix[ix, :] = 0
        counter -= 1
    
    if len(output_osm) != 0:
        print 'Saving conflated data as "%s", open this in JOSM, review and upload. Remember to include "data.udir.no" in source' % output_filename
        output_osm.save(output_filename)
    else:
        print 'Nothing to upload'
    
if __name__ == '__main__':
    import argparse_util
    parser = argparse_util.get_parser("""A tool for assisting with the conflation of openstreetmap and NBR data. 
    You will need JSON to review and upload changes to openstreetmap. 
    Using this tool is therefore completely safe, play around, 
    you changes will not be visible on openstreetmap!

    As a 'working area' you need to supply either a --relation_id or --bounding_box,
    as an NBR data input, you need to supply either a --osm_kommune or --osm_filename.
""")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--relation_id',
                       help="Bounding box as a OSM relation id (e.g. 406130 for Ski kommune)")
    group.add_argument('--bounding_box',
                       help="""Bounding box [west, south, east, north], e.g. '10.8,59.7,10.9,59.7', 
                       use (almost) whatever delimiter you like""")

    parser.add_argument('--osm_kommune', nargs='+',
                        help="""Specify one or more kommune, 
                        either by kommunenummer (e.g. 0213 or 213) or kommunename (e.g. Ski). 
                        If the correct file can not be found, 
                        it will be downloaded from http://obtitus.github.io/barnehagefakta_osm_data/""")
    
    parser.add_argument('--osm_filename', nargs="+", default=[],
                        help="""As an alternative to --osm_kommune. 
                        Specify one or more .osm files (assumed to originate from data.udir.no)""")

    parser.add_argument('--query_template', default="query_template.xml",
                        help="Optionally specify a overpass query xml file, defaults to query_template.xml")
    parser.add_argument('--conflate_cache_filename', default=None,
                        help='Optionally specify a filename for the overpass responce.')
    argparse_util.add_verbosity(parser, default=logging.DEBUG)
    
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)

    area_query = ''
    variables_query = ''
    if args.bounding_box:
        b = re.split('([\d.]+)', args.bounding_box)
        bounding_box = list()
        for ix, item in enumerate(b):
            try:
                f = float(item)
                if ix != 0 and b[ix-1] == '%': # do you really want to know?
                    continue
                bounding_box.append(f)
            except: pass
        assert len(bounding_box) == 4, 'Expected a bounding box with 4 numbers, got: %s numbers: %s' % (len(bounding_box), bounding_box)
        print 'Bounding box:', bounding_box
        
        area_query = '<bbox-query into="_" w="{w}" s="{s}" e="{e}" n="{n}" />'.format(w=bounding_box[0],
                                                                                      s=bounding_box[1],
                                                                                      e=bounding_box[2],
                                                                                      n=bounding_box[3])
    elif args.relation_id:
        searchArea_ref = int(args.relation_id)
        searchArea_ref += 3600000000 # beats me
        variables_query = '<id-query into="searchArea" ref="{ref}" type="area"/>'.format(ref=searchArea_ref)
        area_query = '<area-query from="searchArea" into="_" ref=""/>'
    else:
        print 'Error: You need to supply either --relation_id or --bounding_box, see --help. Exiting...'
        exit(1)

    with open(args.query_template, 'r') as f:
        query = f.read()
    
    query = query.format(variables_query=variables_query,
                         area_query=area_query)
    logger.debug('XML query """%s"""', query)
    overpass_osm = overpass_xml(query, conflate_cache_filename=args.conflate_cache_filename)
    # for key in osm.nsrids:
    #     print key, osm.nsrids[key]

    # print len(osm), osm

    nbr_osms_filenames = args.osm_filename
    if args.osm_kommune:
        for kommune in args.osm_kommune:
            nbr_osms_filenames.extend(get_kommune(kommune))

    nbr_osms = []
    for filename in nbr_osms_filenames:
        xml = file_util.read_file(filename)
        nbr_osms.append(osmapis.OSMnsrid.from_xml(xml))

    if len(nbr_osms) == 0:
        print 'Warning: You need to supply either --osm_kommune and/or --osm_filename, see --help. Exiting...'
        exit(1)
    
    # Combine osm objects
    nbr_osm = osmapis.OSMnsrid()
    for o in nbr_osms:
        for item in o:
            nbr_osm.add(item)

    print 'Saving the combined nbr data as nbr.osm'
    nbr_osm.save('nbr.osm')

    conflate(nbr_osm, overpass_osm, output_filename='out.osm')
