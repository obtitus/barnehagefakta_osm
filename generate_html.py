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
import kommunenummer

from htmldiff import htmldiff
def my_htmldiff(a, b):
    d = htmldiff.HTMLMatcher(a.encode('utf8'), b.encode('utf8'),
                             accurate_mode=True)
    return d.htmlDiff(addStylesheet=False).decode('utf8')

link_template = u'<a href="{href}"\ntitle="{title}">{text}</a>'
# base_url = 'http://obtitus.github.io/barnehagefakta_osm_data/'
# base_url = ''

def get_osm_files(folder):
    for filename in os.listdir(folder):
        filename = os.path.join(folder, filename)
        if filename.endswith('.osm'):
            logger.info('.osm file %s', filename)
            with open(filename) as f:
                data = osmapis.OSMnsrid.from_xml(f.read())
            
            yield filename, data

def not_empty_file(filename):
    """Return True if file does exist and is not empty"""
    #if os.path.exists(filename):
    try:
        with open(filename, 'r') as f:
            c = f.read()
            if c.strip() != '':
                return True
    except Exception as e:
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

def create_pre(dict1, dict_compare):
    tags = '<pre>'
    for key, value in sorted(dict1.items()):
        diff_value = key in dict_compare and dict_compare[key] != dict1[key]
        if diff_value:
            a, b = dict_compare[key], dict1[key]
            value = my_htmldiff(a, b)

        line = '%s = %s\n' % (key, value)
        if diff_value:
            line = '<diff_value>%s</diff_value>' % line
        tags += line
    tags += '</pre>'
    return tags

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
        row.append(kindergarten.tags['name'])

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
            tags = 'FEIL: Flere openstreetmap objekter funnet med no-barnehage:nsrid = %s' % nsrId
        else:
            count_osm += 1
            assert len(osm_data) == 1
            osm_data = osm_data[0]
            osm_data_tags = osm_data.tags
            tags = create_pre(osm_data.tags, kindergarten.tags)

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
            if osm_type_str is not 'node':
                full = '/full'
            osm_url_api = '"https://www.openstreetmap.org/api/0.6/%s/%s%s"' % (osm_type_str, osm_id, full)
            osm_url = 'http://www.openstreetmap.org/%s/%s' % (osm_type_str, osm_id)
            
            try:
                lat, lon = get_lat_lon(osm, osm_data)
            except TypeError:
                pass            # hack
            except Exception as e:
                logger.exception('Unable to get lat/lon from %s %s', osm_data, e)


        # Tags from nbr
        tags_nbr = create_pre(kindergarten.tags, osm_data_tags)
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

def main(osm, data_dir='data', root_output='', template='template.html', index_template='index_template.html'):
    
    with open_utf8(template) as f:
        template = Template(f.read())
    with open_utf8(index_template) as f:
        index_template = Template(f.read())

    index_table = list()
    # counters for bottom of main table (what a mess)
    total_nbr = 0
    total_osm = 0
    for kommune_nr in os.listdir(data_dir):
        folder = os.path.join(data_dir, kommune_nr)
        if os.path.isdir(folder):
            page_filename = os.path.join(root_output, kommune_nr + '.html')
            warning_filename = os.path.join(root_output, 'data', kommune_nr, 'warnings.log')
            last_update_stamp = os.path.getmtime(folder)
            last_update_datetime = datetime.fromtimestamp(last_update_stamp)
            last_update = last_update_datetime.strftime('%Y-%m-%d %H:%M')
            
            logger.info('Kommune folder = %s', folder)

            kommune_name = kommunenummer.nrtonavn[int(kommune_nr)] + ' kommune'
            #title = 'Barnehager i %s kommune (%s)' % (kommune_name, kommune_nr)
            
            table = list()
            info = ''
            info_warning = ''
            count_osm = 0
            count_duplicate_osm = 0
            for filename, data in get_osm_files(folder):
                t, c_osm, c_duplicate_osm = create_rows(osm, data)
                table.extend(t)
                count_osm += c_osm
                count_duplicate_osm += c_duplicate_osm

                if filename.endswith('barnehagefakta.osm'):
                    link = u'<a href="{href}"\ntitle="{title}">\n{text}</a>'.format(href=filename,
                                                                                  title=u"Trykk for å laste ned "+ filename,
                                                                                  text=filename)
                    info += u'<p>{link} inneholder data fra NBR som noder, denne kan åpnes i JOSM.</p>'.format(link=link)
                    
                if filename.endswith('barnehagefakta_familiebarnehager.osm'):
                    link = u'<a href="{href}"\ntitle="{title}">\n{text}</a>'.format(href=filename,
                                                                                  title=u"Trykk for å laste ned "+filename,
                                                                                  text=filename)
                    info += u'<p>Familiebarnehager er vanskeligere å kartlegge, disse ligger derfor i sin egen fil: {link}</p>'.format(link=link)


            if not_empty_file(warning_filename):
                link = u'<a href="{href}"\ntitle="{title}">\n{text}</a>'.format(href=warning_filename,
                                                                                title=u"Sjekk warnings.log",
                                                                                text='warnings.log')
                info_warning += u'<p>Sjekk gjerne {0}</p>'.format(link)
                
            if len(table) != 0:
                total_nbr += len(table)
                total_osm += count_osm
                
                per = (100.*count_osm)/len(table)
                progress = '<meter style="width:100%" value="{value}" min="{min}" max="{max}" optimum="{max}">{per} %</meter>'\
                           .format(value=count_osm,
                                   min=0, max=len(table),
                                   per=per)
                index_table.append((page_filename, u'Vis kommune', [kommune_nr, kommune_name, len(table), count_osm, progress]))
                
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
                    
    info = u"""
    <p>Data fra <a href=https://nbr.udir.no>https://nbr.udir.no</a> og <a href=http://openstreetmap.org> openstreetmap.org</a>.
    Kun barnehager med taggen "no-barnehage:nsrid" blir gjenkjent.
    </p>
    <p>
    Trykk på en av radene i tabellen under for å vise barnehage-data for kommunen.
    </p>
    """
    page = index_template.render(info=info, table=index_table, bottom_row=total)
    index = os.path.join(root_output, 'index.html')
    with open_utf8(index, 'w') as output:
        output.write(page)

    # dump progress to csv
    today = datetime.utcnow()
    td = (today - datetime(1970, 1, 1))
    td_s = td.total_seconds()
    with open('history.csv', 'a') as f:
        f.write('{0},{1},{2}\n'.format(td_s, total_nbr, total_osm))

def get_osm_data():
    xml = update_osm.overpass_nsrid()
    osm = osmapis.OSMnsrid.from_xml(xml)
    # osm_elements = list(update_osm.find_all_nsrid_osm_elements(osm))
    print len(osm.nsrids), osm.nsrids
    return osm

if __name__ == '__main__':
    import argparse_util
    parser = argparse_util.get_parser('Looks for <data_dir>/<kommune_id>/*.osm files and generates html for http://obtitus.github.io/barnehagefakta_osm_data/. The site is generated in the current directory by default and assumes template.html and index_template.html exists in the current directory.')
    parser.add_argument('--data_dir', default='data',
                        help='Specify directory for .osm files, defaults to data/')
    parser.add_argument('--output_dir', default='.',
                        help="Specify output directory, defaults to current directory")        
    parser.add_argument('--template', default='template.html',
                        help="Specify template file for each of the kommune pages, defaults to template.html")
    parser.add_argument('--index_template', default='index_template.html',
                        help="Specify template file for index.html, defaults to index_template.html")
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
         template=args.template, index_template=args.index_template,
         root_output=args.output_dir)
