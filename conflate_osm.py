#!/usr/bin/env python
# -*- coding: utf8

# Standard python imports
import re
import os
import hashlib
import logging
logger = logging.getLogger('barnehagefakta')
# This project
import file_util
import osmapis_nsrid as osmapis
from barnehagefakta_osm import to_kommunenr

def overpass_xml(xml):
    filename = 'conflate_cache_' + hashlib.md5(xml).hexdigest() + '.osm'
    cached, outdated = file_util.cached_file(filename, old_age_days=1)
    if cached is not None and not(outdated):
        print 'Using overpass responce stored as "%s". Delete this file if you wish an updated version' % filename
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
                yield filename2
            if os.path.exists(filename1):
                yield filename1
                break
    else:
        raise BaseException("Could not find barnehagefakta.osm")

def get_kommune(kommune):
    kommune = to_kommunenr(kommune) # now a nicely formatted string e.g. '0213'
    try:
        get_kommune_local(kommune)
    except BaseException:
        urllib.request.urlretrieve('http://obtitus.github.io/barnehagefakta_osm_data/data/%s/%s', kommune, 'barnehagefakta.osm')
        urllib.request.urlretrieve('http://obtitus.github.io/barnehagefakta_osm_data/data/%s/%s', kommune, 'barnehagefakta_familiebarnehager.osm')
        download
        
if __name__ == '__main__':
    import argparse_util
    parser = argparse_util.get_parser('A tool for assisting with the conflation of openstreetmap and NBR data. You will need JSON to review and upload changes to openstreetmap')
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--relation_id', help="Bounding box as a OSM relation id (e.g. 406130 for Ski kommune)")
    group.add_argument('--bounding_box', help="Bounding box [west, south, east, north], e.g. '10.8,59.7,10.9,59.7', use (almost) whatever delimiter you like")

    parser.add_argument('--query_template', default="query_template.xml",
                        help="A overpass query template xml file, defaults to query_template.xml")

    parser.add_argument('--osm_kommune', nargs='+', help='Specify one or more kommune, either by kommunenummer (e.g. 0213 or 213) or kommunename (e.g. Ski). If the correct file can not be found, it will be downloaded from http://obtitus.github.io/barnehagefakta_osm_data/')
    parser.add_argument('--osm_filename', nargs="+", help="As an alternative to --osm_kommune. Specify one or more .osm files (assumed to originate from data.udir.no)")
    
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
    osm = overpass_xml(query)
    for key in osm.nsrids:
        print key, osm.nsrids[key]

    print len(osm), osm

    nbr_osms = list()
    if args.osm_kommune:
        for kommune in args.osm_kommune:
            nbr_osms.append(get_kommune(kommune))
    if args.osm_filename:
        for filename in args.osm_filename:
            xml = file_util.read_file(filename)
            nbr_osms.append(osmapis.OSMnsrid.from_xml(xml))

    if len(nbr_osms) == 0:
        print 'Warning: You need to supply either --osm_kommune and/or --osm_filename, see --help. Exiting...'
        exit(1)
    
    # Combine osm objects
    nbr_osm = osmapis.OSMnsrid()
    for o in nbr_osms:
        for item in o:
            nbr_osm.add(o)
