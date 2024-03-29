#!/usr/bin/env python
# -*- coding: utf8

import json
from datetime import datetime
import codecs
def open_utf8(filename, *args, **kwargs):
    logger.debug('open(%s, %s, %s)', filename, args, kwargs)
    return codecs.open(filename, *args, encoding="utf-8-sig", **kwargs)

import os.path
import logging
logger = logging.getLogger('barnehagefakta.generate_html')
from jinja2 import Template

# This project
import update_osm
import osmapis_nsrid as osmapis
from utility_to_osm.kommunenummer import kommunenummer
from utility_to_osm.generate_html_history_chart import render_history_chart

# from difflib import HtmlDiff
# def my_htmldiff(a, b):
#     d = HtmlDiff()
#     t = d.make_table(a.encode('utf8'), b.encode('utf8'))
#     return t
from utility_to_osm import htmldiff
def my_htmldiff(a, b):
    try:
        d = htmldiff.HTMLMatcher(a.encode('utf8'), b.encode('utf8'),
                                 accurate_mode=True)
        return d.htmlDiff(addStylesheet=False).decode('utf8')
    except:
        d = htmldiff.HTMLMatcher(a, b,
                                 accurate_mode=True)
        return d.htmlDiff(addStylesheet=False)

link_template = u'<a href="{href}"\ntitle="{title}">{text}</a>'
# base_url = 'http://obtitus.github.io/barnehagefakta_osm_data/'
# base_url = ''

def not_empty_file(filename, ignore_missing_file=False):
    """Return True if file does exist and is not empty"""
    #if os.path.exists(filename):
    try:
        with open(filename, 'r') as f:
            c = f.read()
            if c.strip() != '':
                return True
    except Exception as e:
        if not(ignore_missing_file):
            logger.warning('file does not exists "%s", %s', filename, e)
    return False
def get_lat_lon(osm, osm_data):
    way = None
    node = None
    if isinstance(osm_data, osmapis.Relation):
        try:
            way = osm.ways[osm_data.members[0]['ref']]
        except KeyError:
            logger.warning('Not yet supported, unable to get lat/lon from Relations')
            return None
    elif isinstance(osm_data, osmapis.Way):
        way = osm_data
    elif isinstance(osm_data, osmapis.Node):
        node = osm_data
    else:
        raise ValueError('expected osmapis.Relation/Way/Node object, got %s', type(osm_data))

    if way is not None:
        # not a node? just pick the first node in way
        node = osm.nodes[way.nds[0]]

    lat, lon = node.attribs['lat'], node.attribs['lon']
    return lat, lon

def create_pre(dict1, dict_compare, mark_missing_key=True, ignore_keys=('ADDRESS', )):
    tags = '<pre>'
    for key, value in sorted(dict1.items()):
#        if key in ignore_keys:
#            continue
        
        missing_key = key not in dict_compare
        ignore = key in ignore_keys
        diff_value = not(ignore) and not(missing_key) and dict_compare[key] != dict1[key]
        if key == 'capacity' and diff_value: # okey, maybe try and not be so strict with capacity
            diff_value = not(update_osm.compare_capacity(dict_compare[key], dict1[key]))
        
        if diff_value:
            a, b = dict_compare[key], dict1[key]
            value = my_htmldiff(a, b)

        line = '%s = %s\n' % (key, value)
        if diff_value:
            line = '<diff_value>%s</diff_value>' % line

        if mark_missing_key and missing_key and not(ignore):
            line = '<missing_key>%s</missing_key>' % line
            
        tags += line
    tags += '</pre>'
    return tags

def create_osm_url(osm_data):
    if isinstance(osm_data, osmapis.Node):
        osm_type_str = 'node'
    elif isinstance(osm_data, osmapis.Way):
        osm_type_str = 'way'
    elif isinstance(osm_data, osmapis.Relation):
        osm_type_str = 'relation'
    else:
        raise ValueError('osm_data type not recognized, %s, %s', type(osm_data), osm_data)

    osm_id = osm_data.attribs['id']
    full = ''
    if osm_type_str != 'node':
        full = '/full'
    
    osm_url_api = '"https://www.openstreetmap.org/api/0.6/%s/%s%s"' % (osm_type_str, osm_id, full)
    osm_url = 'https://www.openstreetmap.org/%s/%s' % (osm_type_str, osm_id)

    return osm_url, osm_url_api

def create_rows(osm, data):
    table = list()
    count_osm = 0
    count_duplicate_osm = 0
    for kindergarten in sorted(data, key=lambda x: int(x.tags.get('capacity', 0)), reverse=True):
        # shorthands
        nsrId = kindergarten.tags['no-barnehage:nsrid']
        lat, lon = kindergarten.attribs['lat'], kindergarten.attribs['lon']

        row = list()
        # Name
        name_column = kindergarten.tags['name']

        # Tags from OSM
        osm_data = []
        if osm is not None:
            osm_data = osm.nsrids.get(nsrId, [])
        
        tags = ''
        osm_url = None        
        osm_url_api = None
        osm_data_tags = {}
        # osm_xml = None        
        if len(osm_data) == 0:
            tags = 'Fant ingen openstreetmap objekt med no-barnehage:nsrid = %s' % nsrId
        elif len(osm_data) != 1:
            count_duplicate_osm += 1
            tags = 'FEIL: Flere openstreetmap objekter funnet med no-barnehage:nsrid = %s' % nsrId + '\n'
            for item in osm_data:
                href, _ = create_osm_url(item)
                title = href.replace('https://www.', '')
                text = title
                tags += link_template.format(href=href, title=title, text=text) + '\n'
                tags += create_pre(item.tags, kindergarten.tags, mark_missing_key=False)
        else:
            count_osm += 1
            assert len(osm_data) == 1
            osm_data = osm_data[0]
            osm_data_tags = osm_data.tags
            tags = create_pre(osm_data.tags, kindergarten.tags, mark_missing_key=False)

            osm_url, osm_url_api = create_osm_url(osm_data)
            
            try:
                lat, lon = get_lat_lon(osm, osm_data)
            except TypeError:
                pass            # hack
            except Exception as e:
                logger.exception('Unable to get lat/lon from %s %s', osm_data, e)


        # Tags from nbr
        mark_missing_key = True
        if len(osm_data_tags) == 0: mark_missing_key=False # do not mark the 'not found'
        tags_nbr = create_pre(kindergarten.tags, osm_data_tags, mark_missing_key=mark_missing_key)

        row.append(name_column)
        row.append(tags_nbr)
        row.append(tags)
        
        # Links
        links = '<pre>'
        href = 'http://barnehagefakta.no/barnehage/{0}'.format(nsrId)
        title = u'Du blir sendt til barnehagens side på barnehagefakta.no'
        text = u'Besøk på barnehagefakta.no'
        links += link_template.format(href=href, title=title, text=text) + '\n'

        if osm_url is None:
            href = 'http://www.openstreetmap.org/#map=17/{lat}/{lon}'.format(lat=lat,lon=lon)
        else:
            href = osm_url
        title = u'Se posisjonen i openstreetmap'
        text = u'Besøk på openstreetmap.org'
        links += link_template.format(href=href, title=title, text=text) + '\n'
        
        href = 'https://nbr.udir.no/status/rapporterfeil/{0}'.format(nsrId)
        title = u'Du blir sendt til nbr.uio.no hvor du kan melde om feil i data-settet. Vurder også å melde fra til kommunen.'
        text = u'Meld feil til NBR'
        links += link_template.format(href=href, title=title, text=text) + '\n'

        href = 'http://www.openstreetmap.org/note/new#map=17/{lat}/{lon}'.format(lat=lat,lon=lon)
        title = u'Gjør openstreetmap mappere oppmerksom på feil i kartet.'
        text = 'Meld feil til OSM'
        links += link_template.format(href=href, title=title, text=text) + '\n'
        
        href = 'http://www.openstreetmap.org/edit?editor=id&lat={lat}&lon={lon}&zoom=17'.format(lat=lat,lon=lon)
        title = u'Du blir sendt til openstreetmap sin web-editor'
        text = 'Editer OSM'
        links += link_template.format(href=href, title=title, text=text)

        website_address = ''
        if len(osm_data_tags) == 0:
            website_address = kindergarten.tags.get('contact:website', '')
        else:
            # use website from osm
            website_address = osm_data_tags.get('contact:website', '')

        if website_address != '':
            links += '\n' + link_template.format(href=website_address,
                                                 title='website',
                                                 text='Barnehagens webside')
        
        links += '</pre>'
        row.append(links)

        # Map
        if osm_url_api is None: osm_url_api = 'null'
        # if osm_xml is None: osm_xml = 'null'        
        # _map = '<div id="wrapper" style="width:256px;">'
        _map = '<div id="map{0}" style="width: 256px; height: 256px;position: relative"></div>'.format(nsrId)
        _map += '<script>create_map(map{nsrId}, {lat}, {lon}, {osm_url_api})</script>'.format(nsrId=nsrId,
                                                                                         osm_url_api=osm_url_api,
                                                                                         lat=lat,
                                                                                         lon=lon)
        # _map += '</div>'
        row.append(_map)

        table.append(row)

    return table, count_osm, count_duplicate_osm
        #yield row

def main(osm, data_dir='data', root_output='',
         root=''):

    index_template = os.path.join(root, 'templates', 'index_template.html')
    template = os.path.join(root, 'templates', 'kommune_page_template.html')
    
    with open_utf8(template) as f:
        template = Template(f.read())
    with open_utf8(index_template) as f:
        index_template = Template(f.read())

    kommune_nr2name, kommune_name2nr = kommunenummer(cache_dir=data_dir)
    index_table = list()
    # counters for bottom of main table (what a mess)
    total_nbr = 0
    total_osm = 0
    for kommune_nr in sorted(os.listdir(data_dir)):
        folder = os.path.join(data_dir, kommune_nr)
        if os.path.isdir(folder):
            try:
                kommune_name = kommune_nr2name[int(kommune_nr)] + ' kommune'
            except KeyError as e:
                logger.warning('Could not translate kommune_nr = %s to a name. Skipping', kommune_nr)
                #kommune_name = 'ukjent'
                continue

            page_filename = os.path.join(root_output, kommune_nr + '.html')
            warning_filename = os.path.join(root_output, 'data', kommune_nr, 'warnings.log')
            discontinued_filename = os.path.join(root_output, 'data', kommune_nr, 'barnehagefakta_discontinued.csv')
            last_update_stamp = os.path.getmtime(folder)
            last_update_datetime = datetime.fromtimestamp(last_update_stamp)
            last_update = last_update_datetime.strftime('%Y-%m-%d %H:%M')
            
            logger.info('Kommune folder = %s', folder)

            table = list()
            info = ''
            info_warning = ''
            count_osm = 0
            count_duplicate_osm = 0
            for filename, data in update_osm.get_osm_files(folder):
                t, c_osm, c_duplicate_osm = create_rows(osm, data)
                table.extend(t)
                count_osm += c_osm
                count_duplicate_osm += c_duplicate_osm
                filename_base = os.path.basename(filename)
                if filename.endswith('barnehagefakta.osm'):
                    link = u'<a href="{href}"\ntitle="{title}">\n{text}</a>'.format(href=filename,
                                                                                    title=u"Trykk for å laste ned "+ filename_base,
                                                                                    text=filename_base)
                    info += u'<p>{link} inneholder data fra NBR som noder, denne kan åpnes i JOSM.</p>'.format(link=link)
                    
                if filename.endswith('barnehagefakta_familiebarnehager.osm'):
                    link = u'<a href="{href}"\ntitle="{title}">\n{text}</a>'.format(href=filename,
                                                                                    title=u"Trykk for å laste ned "+filename_base,
                                                                                    text=filename_base)
                    info += u'<p>Familiebarnehager er vanskeligere å kartlegge, disse ligger derfor i sin egen fil: {link}</p>'.format(link=link)


            if not_empty_file(warning_filename):
                link = u'<a href="{href}"\ntitle="{title}">\n{text}</a>'.format(href=warning_filename,
                                                                                title=u"Sjekk gjerne warnings.log",
                                                                                text='warnings.log')
                info_warning += u'<p>Sjekk gjerne {0}</p>\n'.format(link)

            if not_empty_file(discontinued_filename, ignore_missing_file=True):
                link = u'<a href="{href}"\ntitle="{title}">\n{text}</a>'.format(href=discontinued_filename,
                                                                                title=u"Sjekk gjerne discontinued.csv",
                                                                                text='discontinued.csv')
                info_warning += u'<p>Sjekk gjerne {0} for barnehager i nbr sitt register som ikke ligger i barnehagefakta.no</p>\n'.format(link)
                
            if len(table) != 0:
                total_nbr += len(table)
                total_osm += count_osm
                
                per = (100.*count_osm)/len(table)
                progress = '<meter style="width:100%" value="{value}" min="{min}" max="{max}" optimum="{max}">{per} %</meter>'\
                           .format(value=count_osm,
                                   min=0, max=len(table),
                                   per=per)

                count_duplicate_osm_str = '0'
                if count_duplicate_osm != 0:
                    count_duplicate_osm_str = '<p style="background-color:red">%s</p>' % count_duplicate_osm
                
                index_table.append((page_filename, u'Vis kommune', [kommune_nr, kommune_name, len(table), count_osm,
                                                                    count_duplicate_osm_str, progress]))
                
                page = template.render(kommune_name=kommune_name,
                                       kommune_nr=kommune_nr,
                                       table=table, info=info,
                                       info_warning=info_warning,
                                       last_update=last_update)
                # Kommune-folder
                with open_utf8(page_filename, 'w') as output:
                    output.write(page)
                
                    
    # total:
    per = (100.*total_osm)/total_nbr
    progress = '<meter style="width:100%" value="{value}" min="{min}" max="{max}" optimum="{max}">{per} %</meter>'\
               .format(value=total_osm,
                       min=0, max=total_nbr,
                       per=per)
    total = ['Sum', '', total_nbr, total_osm, progress]
                    
    # dump progress to csv
    today = datetime.utcnow()
    td = (today - datetime(1970, 1, 1))
    td_s = td.total_seconds()
    with open('history.csv', 'a') as f:
        f.write('{0},{1},{2}\n'.format(td_s, total_nbr, total_osm))


    info = u"""
    <p>Data fra <a href=https://nbr.udir.no>https://nbr.udir.no</a> og <a href=http://openstreetmap.org> openstreetmap.org</a>.
    Kun barnehager med taggen "no-barnehage:nsrid" blir gjenkjent.
    </p>
    <p>
    Trykk på en av radene i tabellen under for å vise barnehage-data for kommunen.
    </p>
    """
    chart = render_history_chart(root)

    page = index_template.render(info=info, table=index_table, bottom_row=total, chart=chart, now=td_s)
    index = os.path.join(root_output, 'index.html')
    with open_utf8(index, 'w') as output:
        output.write(page)


def get_osm_data():
    xml = update_osm.overpass_nsrid()
    osm = osmapis.OSMnsrid.from_xml(xml)
    # osm_elements = list(update_osm.find_all_nsrid_osm_elements(osm))
    print('Overpass returned', len(osm.nsrids), 'objects')#, osm.nsrids

    for item in osm:
        if 'doNotImportAddress' in item.tags:
            err_msg = 'Found doNotImportAddress = %s on no-barnehage:nsrid=%s, remove key!' % (item.tags['doNotImportAddress'],
                                                                                               item.nsrids[key])
            logger.error(err_msg)
            raise ValueError(err_msg)
        
    return osm

if __name__ == '__main__':
    from utility_to_osm import argparse_util
    parser = argparse_util.get_parser('Looks for <data_dir>/<kommune_id>/*.osm files and generates html for http://obtitus.github.io/barnehagefakta_osm_data/. The site is generated in the current directory by default and assumes template.html and index_template.html exists in the template directory.')
    parser.add_argument('--data_dir', default='data',
                        help='Specify directory for .osm files, defaults to data/')
    parser.add_argument('--root', default='.',
                        help="Specify input/output directory, defaults to current directory. Expects a templates folder with required html and javascript templates")
    parser.add_argument('--no-overpass', default=False, action='store_true',
                        help="Do not call the openstreetmap overpass api looking for no-barnehage:nsrid")
    argparse_util.add_verbosity(parser, default=logging.WARNING)

    args = parser.parse_args()
    
    logging.basicConfig(level=args.loglevel)

    if args.no_overpass:
        osm = None
    else:
        osm = get_osm_data()
    
    main(osm, args.data_dir,
         root=args.root)
