# standard python imports
import os

# non standard imports, fixme: merge generate_html.py
from htmldiff import htmldiff
def print_html_diff(a, b, addStylesheet=True):
    d = htmldiff.HTMLMatcher(a.encode('utf8'), b.encode('utf8'),
                             accurate_mode=True)
    html = d.htmlDiff(addStylesheet=addStylesheet).decode('utf8')
    try:
        from IPython.core.display import display, HTML
        display(HTML(html))
    except ImportErrror as e:
        print e

# This project
import update_osm
import osmapis_nsrid as osmapis
import update_osm

def get_osm_data():
    xml = update_osm.overpass_nsrid()
    osm = osmapis.OSMnsrid.from_xml(xml)
    # osm_elements = list(update_osm.find_all_nsrid_osm_elements(osm))
    print len(osm.nsrids), osm.nsrids
    return osm

def merge_kindergarten(osm, kindergarten):
    nsrid = kindergarten.tags['no-barnehage:nsrid']
    if nsrid not in osm.nsrids:
        return True
    assert len(osm.nsrids[nsrid]) == 1

    nbr_data_tags = kindergarten.tags
    osm_data = osm.nsrids[nsrid][0]
    osm_data_tags = osm_data.tags
    for key in nbr_data_tags:
        promt_user = False
        update = False
        if key in osm_data_tags:
            if osm_data_tags[key] == nbr_data_tags[key]:
                pass
            else:
                print '\n==== %s key = "%s", nbr != osm: "%s" != "%s" ====' % (nsrid, key, nbr_data_tags[key], osm_data_tags[key])
                print_html_diff(osm_data_tags[key], nbr_data_tags[key])
                if key in ('operator', 'name'): # skip these for now
                    print 'Skipping\n'
                elif key in ('contact:email', 'capacity'):
                    promt_user = False
                    update = True
                    print 'Updating\n'
                else:
                    promt_user = True

        else:
            print '\n=== %s key = "%s", "%s" missing from osm, Add? ===' % (nsrid, key, nbr_data_tags[key])
            promt_user = True

        if promt_user:
            print 'OSM keys are'
            for osm_key in sorted(osm_data_tags.keys()): print '%s = %s' % (osm_key, osm_data_tags[osm_key])
            
            user_input = raw_input('>>[y] ')
            if user_input.lower() in ('y', ''):
                update = True
            elif user_input.lower() in ('s', 'n'):
                continue
            elif user_input.lower() in ('q', 'e'):
                return False
            else:
                print 'unkown user_input, breaking.', repr(user_input)
                return False

        if update:
            osm_data_tags[key] = nbr_data_tags[key]
            osm_data.attribs['action'] = 'modify'
            print 'Corrected to %s = %s\n' % (key, nbr_data_tags[key])

    return True

def compare_all(osm, data_dir):
    for kommune_nr in os.listdir(data_dir):
        folder = os.path.join(data_dir, kommune_nr)
        if not(os.path.isdir(folder)): continue

        for filename, data in update_osm.get_osm_files(folder):
            for kindergarten in data:
                success = merge_kindergarten(osm, kindergarten)
                if success == False:
                    return osm

if __name__ == '__main__':
    data_dir = 'barnehagefakta_osm_data/data'
    output_filename = 'update_osm_all.osm'
    osm = get_osm_data()

    compare_all(osm, data_dir)

    print 'Saving conflated data as "%s", open this in JOSM, review and upload. Remember to include "data.udir.no" in source' % output_filename
    osm.save(output_filename)
