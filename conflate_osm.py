#!/usr/bin/env python
# -*- coding: utf8

# Standard python imports
import re
import os
import urllib2
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
    osm = o.interpreter(xml)

    print 'Overpass responce stored as %s' % filename
    osm.save(filename)

    return osm

def get_kommune_local(kommune):
    for root, dirs, files in os.walk('.'): # fixme
        if kommune in dirs:
            filename1 = os.path.join(root, kommune, kommune + '_barnehagefakta.osm')
            filename2 = os.path.join(root, kommune, kommune + '_barnehagefakta_familiebarnehager.osm')
            if os.path.exists(filename2):
                logger.info('Found %s', filename2)
                yield filename2
            if os.path.exists(filename1):
                logger.info('Found %s', filename1)
                yield filename1
                break
    else:
        raise BaseException("Could not find barnehagefakta.osm")

def download(root_url, directory, filename):
    url = os.path.join(root_url, directory, filename) # should probably use some html join, but I know the input...
    filename = os.path.join(directory, filename)
    response = urllib2.urlopen(url)
    content = response.read()
    file_util.write_file(filename, content)
    return filename

def get_kommune(kommune):
    kommune = to_kommunenr(kommune) # now a nicely formatted string e.g. '0213'
    try:
        return list(get_kommune_local(kommune))
    except BaseException as e:
        logger.info('Failed to find local barnehagefakt.osm file: %s. Downloading...', e)
        f1 = download('http://obtitus.github.io/barnehagefakta_osm_data/data', kommune,
                      kommune + '_barnehagefakta.osm')
        f2 = download('http://obtitus.github.io/barnehagefakta_osm_data/data', kommune,
                      kommune + '_barnehagefakta_familiebarnehager.osm')
        return [f1, f2]

def score_similarity_strings(nbr_name, overpass_name):
    """Given two strings, give a score for their similarity
    100 for match and +10 for each matching word. Case-insensitive"""
    # fixme: there are a number of good python tools for looking at similar strings
    # use one! This will not catch spelling errors.
    if nbr_name is None or overpass_name is None:
        return 0

    nbr_name, overpass_name = nbr_name.lower(), overpass_name.lower()
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

    lat_lon = get_lat_lon(overpass_osm, overpass_element) # fixme, only returns 1 node
    if lat_lon is not None:
        overpass_lat, overpass_lon = lat_lon
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

def add_missing_tags(nbr_element, overpass_element):
    """For all keys in a, add the value to b if missing from b"""
    ret = dict(overpass_element.tags)
    for key in nbr_element.tags:
        if key not in overpass_element.tags:
            logger.debug('Adding tag %s = %s', key, nbr_element.tags[key])
            ret[key] = nbr_element.tags[key]
    return ret

def parse_user_input_tag_change(user_input):
    """ Tries to be as friendly to the user as possible
    >>> parse_user_input_tag_change('name="corrected name"')
    ('name', 'corrected name')
    >>> parse_user_input_tag_change('"name" = "corrected name"')
    ('name', 'corrected name')
    >>> parse_user_input_tag_change(' "name" = "corrected name" ')
    ('name', 'corrected name')
    >>> parse_user_input_tag_change('name=corrected')
    ('name', 'corrected')
    >>> parse_user_input_tag_change('name=corrected name')
    ('name', 'corrected name')
    >>> parse_user_input_tag_change('"name"=corrected')
    ('name', 'corrected')
    >>> parse_user_input_tag_change('"amenity"="foo"')
    ('amenity', 'foo')
    >>> parse_user_input_tag_change('"source"=""')
    ('source', '')
    >>> parse_user_input_tag_change('source=')
    ('source', '')
    >>> parse_user_input_tag_change('k="name" v="Corrected name"')
    ('name', 'Corrected name')
    >>> parse_user_input_tag_change('k="name"  v="Corrected name"')
    ('name', 'Corrected name')
    >>> parse_user_input_tag_change('k="name"v="Corrected name"')
    ('name', 'Corrected name')
    >>> parse_user_input_tag_change('k=name v="Corrected name"')
    ('name', 'Corrected name')
    >>> parse_user_input_tag_change('k=name v=Corrected')
    ('name', 'Corrected')
    >>> parse_user_input_tag_change('k=name v=Corrected name')
    ('name', 'Corrected name')
    >>> parse_user_input_tag_change("k='name' v='Corrected name'")
    ('name', 'Corrected name')
    >>> parse_user_input_tag_change("k='contact:website' v='http://www.ski.kommune.no/BARNEHAGER/Vestveien/'")
    ('contact:website', 'http://www.ski.kommune.no/BARNEHAGER/Vestveien/')
    >>> parse_user_input_tag_change("'contact:website'='http://www.ski.kommune.no/BARNEHAGER/Vestveien/'")
    ('contact:website', 'http://www.ski.kommune.no/BARNEHAGER/Vestveien/')
    >>> parse_user_input_tag_change("contact:website=http://www.ski.kommune.no/BARNEHAGER/Vestveien/")
    ('contact:website', 'http://www.ski.kommune.no/BARNEHAGER/Vestveien/')
    """
    user_input = user_input.replace("'", '"') # replace any single quotes with double quotes
    
    reg0 = re.search('k="?([\w:-]+)"?\s*v="?([^"]*)"?', user_input)
    reg1 = re.search('"?([\w:-]+)["\s]*=["\s]*([^"]*)"?', user_input)
    ret = None
    if reg0:
        ret = reg0.group(1), reg0.group(2)
    elif reg1:
        ret = reg1.group(1), reg1.group(2)
    
    return ret


def add_tags(nbr_element, overpass_element):
    """For all keys in a, add the value to b if missing from b,
    then query the user if he wants to make further adjustments
    INPLACE!"""
    ret = add_missing_tags(nbr_element, overpass_element)
    overpass_element.tags = ret
    print 'Missing tags added, is now """%s"""' % overpass_element
    print 'would you like to make further adjustments to the tags?'
    for key in nbr_element.tags:
        if nbr_element.tags[key] != overpass_element.tags[key]:
            print 'nbr != osm: "%s"="%s" != "%s"="%s"' % (key, nbr_element.tags[key],
                                                          key, overpass_element.tags[key])
    for key in overpass_element.tags:
        if key not in nbr_element.tags:
            print 'not in nbr data: "%s"="%s"' % (key, overpass_element.tags[key])
        
    while True:
        print ('To modify a tag, type e.g. name="Corrected name" '
               'or k="name" v="Corrected name", '
               'blank value deletes the tag, press enter to continue.')

        user_input = raw_input('>> ')
        if user_input.strip() in ("", "q"): break
        
        ret = parse_user_input_tag_change(user_input)
        if ret is not None:
            key, value = ret[0], ret[1]
            if value in ("", None):
                print 'Removing k="%s"' % (key)
                del overpass_element.tags[key]
            else:
                print 'Modifying k="%s" v="%s"' % (key, value)
                overpass_element.tags[key] = value
                
        else:
            print 'Unrecognized input "%s", please try to express yourself more clearly, or fix me' % user_input

    return user_input

def get_all_referenced(lst, osm, recursion=0):
    # there is probably a better way to do this
    assert recursion < 10

    logger.debug('lst = (%s) %s', type(lst), lst)
    for item in lst:
        logger.debug('lst = (%s) %s', type(item), item)
        if isinstance(item, osmapis.Relation):
            yield item
            for i in get_all_referenced(item.members, osm, recursion=recursion+1):
                yield i
        elif isinstance(item, osmapis.Way):
            yield item
            for i in get_all_referenced(item.nds, osm, recursion=recursion+1):
                yield i
        elif isinstance(item, osmapis.Node):
            yield item
        elif isinstance(item, int):
            n = osm.nodes[item]
            assert isinstance(n, osmapis.Node)
            yield n
        elif isinstance(item, dict) and 'type' in item:
            if item['type'] == 'node':
                n = osm.nodes[item['ref']]
                assert isinstance(n, osmapis.Node)
                yield n
            elif item['type'] == 'way':
                w = osm.ways[item['ref']]
                assert isinstance(w, osmapis.Way)
                yield w
                for i in get_all_referenced([w], osm, recursion=recursion+1):
                    yield i
            elif item['type'] == 'rel':
                r = osm.relations[item['ref']]
                assert isinstance(r, osmapis.Relation)
                yield r
                for i in get_all_referenced([r], osm, recursion=recursion+1):
                    yield i
            else:
                raise ValueError('%d, Expected type way or node, not %s, %s' % (recursion, type(item), item))
        else:
            raise ValueError('%d, Expected node/way/relation, not %s, %s' % (recursion, type(item), item))

def conflate(nbr_osm, overpass_osm, output_filename='out.osm'):
    #original_osm = osmapis.OSMnsrid.from_xml(overpass_osm.to_xml()) # inconvenient way of getting a copy

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
    score_matrix[np.where(score_matrix < quantile)] = 0

    modified = list()
    m = np.nanmax(score_matrix, axis=1)
    ix_sort = np.argsort(m)
    for ix in ix_sort[::-1]: # For each nbr node, starting with the higest scoring
        nbr_element = nbr_elements[ix]
        nbr_element_str = u'nsrid = %s, %s' % (nbr_element.tags['no-barnehage:nsrid'], nbr_element.tags['name'])
        
        # Go trough all potensial matches, starting with the most likely.
        jx_sort = list(np.argsort(score_matrix[ix, :]))
        jx_sort.reverse()
        possible_match = list() # build a list of potensial matches
        found = False
        for jx in jx_sort:
            s = score_matrix[ix, jx]
            if s < quantile:
                break

            if is_perfect_match(nbr_elements[ix].tags, overpass_elements[jx].tags):
                print 'Found perfect match between {nbr} and {osm}, score: ({s}) continuing'.\
                    format(nbr=nbr_elements[ix], osm=overpass_elements[jx], s=s)
                found = True
                break
            
            possible_match.append((s, overpass_elements[jx]))

        logger.debug('possible_match = %s, %s', len(possible_match), possible_match)
        if found is False and len(possible_match) == 0:
            print 'No likely match found for %s' % (nbr_element_str)

        if len(possible_match) == 0:
            continue
        elif len(possible_match) == 1:
            print u'\n{h} Found {num} possible match for {name} {h}'\
                .format(h='='*5, num=1, name=nbr_element_str)
        else:                   # Reduces the list of potensiall matches to 1
            print u'\n{h} Found {num} possible matches for {name}, please choose [index] {h}'\
                .format(h='='*5, num=len(possible_match), name=nbr_element_str)

            for ix, (s, overpass_element) in enumerate(possible_match):
                print u'[index] = [{ix}], score = {score}, tags = {tags}'\
                    .format(ix=ix, score=s, tags=overpass_element.tags)
            user_input = raw_input('enter index ("s" to skip): ')
            if user_input == 's': continue
            try:
                possible_match = [possible_match[int(user_input)]] # length 1 list with users-match
            except:
                print ('Stupid user, Error, invalid index {ix}, expecting an integer between 0 and {len}'
                       ', skipping since you are being difficult').format(ix=user_input, len=len(possible_match)-1)
                continue

        assert len(possible_match) == 1
        s, possible_match = possible_match[0]
        print 'Score = {s}, Please confirm match: Is nbr="""\n{nbr}""", the same as "{osm_name}" osm="""\n{osm}"""?'\
            .format(s=s, osm_name=possible_match.tags.get('name').encode('utf-8'), nbr=nbr_element, osm=possible_match)
        
        print "enter 'y' to confirm, 's' or blank to skip to the next one, 'q' to save and quit or ctrl-c to quit"
        user_input = raw_input('> ')
        if user_input.lower() == 'y':
            user_input2 = add_tags(nbr_element, possible_match)
            possible_match.attribs['action'] = 'modify'
            modified.append(possible_match)
            
            if user_input2.lower() == 'q': break
        elif user_input.lower() == 's':
            continue
        elif user_input.lower() == 'q':
            break

    try:
        all_modified = list(get_all_referenced(modified, overpass_osm))
        logger.debug('all_modified=%s',all_modified)
    except Exception as e:
        logger.exception('I have a hack to clean up the .osm files by removing un-modified objects, this failed with %s', e)
        all_modified = overpass_osm
    
    for elem in overpass_osm:
        if not(elem) in all_modified:
            overpass_osm.discard(elem)
        
    if len(modified) != 0:
        print 'Saving conflated data as "%s", open this in JOSM, review and upload. Remember to include "data.udir.no" in source' % output_filename
        overpass_osm.save(output_filename)
    else:
        print 'No changes made, nothing to upload'
    
if __name__ == '__main__':
    import argparse_util
    parser = argparse_util.get_parser("""A tool for assisting with the conflation of openstreetmap and NBR data. 
    You will need JSON to review and upload changes to openstreetmap. 
    Using this tool is therefore completely safe, play around, 
    you changes will not be visible on openstreetmap!

    As a 'working area' you need to supply either a --relation_id or --bounding_box,
    as an NBR data input, you need to supply either a --osm_kommune or --osm_filename.
    """, epilog='Example: ./conflate_osm.py --relation_id 406130 --osm_kommune Ski')
    
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
