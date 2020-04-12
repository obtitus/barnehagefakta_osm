import logging
logger = logging.getLogger('barnehagefakta.osmapis_nsrid')

from utility_to_osm.osmapis import osmapis
from utility_to_osm.osmapis.osmapis import *
#from osmapis import *

class OSMnsrid(osmapis.OSM):
    """Adds the container nsrids to osmpais.OSM, 
    where the dictionary key is the no-barnehage:nsrid value
    and the value is a list (hopefully length 1) with a 
    osmapis.Node/osmapis.Way/osmapis.Relation object.
    Example usage
    o = OSMnsrid.from_xml(xml)
    o.nsrids['3234487807']"""
    
    def __init__(self, *args, **kwargs):
        self.nsrids = {}
        super(OSMnsrid, self).__init__(*args, **kwargs)
    
    def add(self, item):
        if 'no-barnehage:nsrid' in item.tags:
            key = item.tags['no-barnehage:nsrid']
            if key in self.nsrids:
                logger.error('Multiple objects with no-barnehage:nsrid found please fix this, %s, %s', item, self.nsrids[key])
                self.nsrids[key].append(item)
            else:
                self.nsrids[key] = [item]

        return super(OSMnsrid, self).add(item)

    def discard(self, item):
        if 'no-barnehage:nsrid' in item.tags:
            key = item.tags['no-barnehage:nsrid']
            self.nsrids.pop(key, None)
            
        return super(OSMnsrid, self).discard(item)

osmapis.wrappers["osm"] = OSMnsrid
