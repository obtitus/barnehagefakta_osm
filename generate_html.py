#!/usr/bin/env python
# -*- coding: utf8

import json
import codecs
import os.path
import logging
logger = logging.getLogger('barnehagefakta.generate_html')
# non standard
import osmapis
from jinja2 import Template
# This project
import update_osm
import kommunenummer

link_template = u'<a href="{href}"\ntitle="{title}">\n{text}</a>'
base_url = 'http://obtitus.github.io/barnehagefakta_osm_data/'

def get_osm_files(folder):
    for filename in os.listdir(folder):
        filename = os.path.join(folder, filename)
        if filename.endswith('.osm'):
            logger.info('.osm file %s', filename)
            with open(filename) as f:
                data = osmapis.OSM.from_xml(f.read())
            
            yield filename, data

def get_lat_lon(osm, osm_data):
    try:
        lat, lon = osm_data.attribs['lat'], osm_data.attribs['lon']
    except KeyError:
        # not a node? Lets try this (just pick the first node in way/relation)
        n = osm.nodes[osm_data.nds[0]]
        lat, lon = n.attribs['lat'], n.attribs['lon']
    return lat, lon

def create_rows(osm, data):
    table = list()
    count_osm = 0
    count_duplicate_osm = 0
    for kindergarten in data:
        # shorthands
        nsrId = kindergarten.tags['no-barnehage:nsrid']
        lat, lon = kindergarten.attribs['lat'], kindergarten.attribs['lon']

        row = list()
        # Name
        row.append(kindergarten.tags['name'])
        # Tags from nbr
        tags = '<pre>'
        for key, value in sorted(kindergarten.tags.items()):
            tags += '%s = %s\n' % (key, value)
        tags += '</pre>'
        row.append(tags)

        # Tags from OSM
        osm_data = list(update_osm.find_all_nsrid_osm_elements(osm, nsrid=nsrId))
        tags = ''
        if len(osm_data) == 0:
            tags = 'Fant ingen openstreetmap objekt med no-barnehage:nsrid = %s' % nsrId
        elif len(osm_data) != 1:
            count_duplicate_osm += 1
            tags = 'FEIL: Flere openstreetmap objekter funnet med no-barnehage:nsrid = %s' % nsrId
        else:
            count_osm += 1
            assert len(osm_data) == 1
            osm_data = osm_data[0]
            tags = '<pre>'
            for key, value in sorted(osm_data.tags.items()):
                tags += '%s = %s\n' % (key, value)
            tags += '</pre>'
            try:
                lat, lon = get_lat_lon(osm, osm_data)
            except Exception as e:
                logger.exception('Unable to get lat/lon from %s: %s', osm_data, e)
        row.append(tags)
        
        # Links
        links = '<pre>'
        href = 'http://barnehagefakta.no/barnehage/{0}'.format(nsrId)
        title = u'Du blir sendt til barnehagens side på barnehagefakta.no'
        text = u'Besøk på barnehagefakta.no'
        links += link_template.format(href=href, title=title, text=text)
        
        href = 'https://nbr.udir.no/status/rapporterfeil/{0}'.format(nsrId)
        title = u'Du blir sendt til nbr.uio.no hvor du kan melde om feil i data-settet. Vurder også å melde fra til kommunen.'
        text = u'Meld feil til NBR'
        links += link_template.format(href=href, title=title, text=text)

        href = 'http://www.openstreetmap.org/note/new#map=17/{lat}/{lon}'.format(lat=lat,lon=lon)
        title = u'Gjør openstreetmap mappere oppmerksom på feil i kartet.'
        text = 'Meld feil til OSM'
        links += link_template.format(href=href, title=title, text=text)
        
        href = 'http://www.openstreetmap.org/edit?editor=id&lat={lat}&lon={lon}&zoom=17'.format(lat=lat,lon=lon)
        title = u'Du blir sendt til openstreetmap sin web-editor'
        text = 'Editer OSM'
        links += link_template.format(href=href, title=title, text=text)
        
        links += '</pre>'
        row.append(links)

        # Map
        _map = '<div id="wrapper", style="width:256px;">'
        _map += '<div id="map{0}", style="width: 256px; height: 256px;position: absolute"></div>'.format(nsrId)
        _map += '<script>create_map(map{nsrId}, {lat}, {lon})</script>'.format(nsrId=nsrId,
                                                                                lat=lat,
                                                                                lon=lon)
        _map += '</div>'
        row.append(_map)

        table.append(row)

    return table, count_osm, count_duplicate_osm
        #yield row

def main(osm, root='data', template='template.html', index_template='index_template.html'):
    with open(template) as f:
        template = Template(f.read())
    with open(index_template) as f:
        index_template = Template(f.read())

    index_table = list()
    for kommune_nr in os.listdir(root):
        folder = os.path.join(root, kommune_nr)
        if os.path.isdir(folder):
            page_filename = kommune_nr + '.html'
            
            logger.info('Kommune folder = %s', folder)

            kommune_name = kommunenummer.nrtonavn[int(kommune_nr)]
            title = 'Barnehager i %s kommune (%s)' % (kommune_name, kommune_nr)
            
            table = list()
            info = ''
            count_osm = 0
            count_duplicate_osm = 0
            for filename, data in get_osm_files(folder):
                t, c_osm, c_duplicate_osm = create_rows(osm, data)
                table.extend(t)
                count_osm += c_osm
                count_duplicate_osm += c_duplicate_osm

                if filename.endswith('barnehagefakta.osm'):
                    link = u'<a href="{href}"\ntitle="{title}">\n{text}</a>'.format(href=base_url+filename,
                                                                                  title=filename,
                                                                                  text=filename)
                    info += 'For JSON, last ned: {link}.'.format(link=link)
                    
                if filename.endswith('barnehagefakta_familiebarnehager.osm'):
                    link = u'<a href="{href}"\ntitle="{title}">\n{text}</a>'.format(href=base_url+filename,
                                                                                  title=filename,
                                                                                  text=filename)
                    info += u' Familiebarnehager er vanskeligere å kartlegge, disse ligger derfor i sin egen fil: {link}'.format(link=link)
                    
            if len(table) != 0:
                index_table.append((base_url+page_filename, u'Vis kommune', [kommune_nr, kommune_name, len(table), count_osm]))
                
                page = template.render(title=title, table=table, info=info)
                # Kommune-folder
                with codecs.open(page_filename, 'w', "utf-8-sig") as output:
                    output.write(page)

    info = u"""
    Data fra <a href=https://nbr.udir.no>https://nbr.udir.no</a> og <a href=http://openstreetmap.org> openstreetmap.org</a>
    Trykk på en av radene i tabellen under for å vise barnehage-data for kommunen.
    """
    page = index_template.render(info=info, table=index_table)
    with codecs.open('index.html', 'w', "utf-8-sig") as output:
        output.write(page)

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    
    xml = update_osm.overpass_nsrid()
    osm = osmapis.OSM.from_xml(xml)
    osm_elements = list(update_osm.find_all_nsrid_osm_elements(osm))
    print len(osm_elements), osm_elements
    
    main(osm, 'data')
    
    # for root, dirs, files in os.walk(root):
        
    #     for f in files:
    #         if f.endswith('OUTDATED.json'):
    #             try:
    #                 reg = re.search('nbrId(\d+)-(\d+-\d+-\d+)-OUTDATED.json', f)
