# -*- coding: utf-8 -*-

# Standard python imports
import json
import unittest
# non standard
import osmapis
# This project
import update_osm
from barnehagefakta_osm import create_osmtags

# Example responses from overpass api, when searcing for a single no-barnehage:nsrid.
reply_node ="""<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="Overpass API">
<note>The data included in this document is from www.openstreetmap.org. The data is made available under ODbL.</note>
<meta osm_base="2015-08-27T15:24:02Z"/>

  <node id="3717078773" lat="59.7211000" lon="10.8400000" version="1" timestamp="2015-08-27T15:21:03Z" changeset="33623930" uid="36147" user="Øystein Bjørndal">
    <tag k="amenity" v="kindergarten"/>
    <tag k="capacity" v="18"/>
    <tag k="contact:phone" v="64877130"/>
    <tag k="max_age" v="5"/>
    <tag k="min_age" v="3"/>
    <tag k="name" v="Spilloppen barnehage"/>
    <tag k="no-barnehage:nsrid" v="1016218"/>
    <tag k="opening_hours" v="07:30-16:30"/>
    <tag k="operator" v="Ski Kvinne &amp; Familieforbund"/>
    <tag k="operator:type" v="private"/>
    <tag k="start_date" v="1990-01-01"/>
  </node>

</osm>
"""

reply_way = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="Overpass API">
<note>The data included in this document is from www.openstreetmap.org. The data is made available under ODbL.</note>
<meta osm_base="2015-09-06T17:28:02Z"/>

  <node id="3234456500" lat="59.7210207" lon="10.8400324" version="1" timestamp="2014-12-14T15:09:35Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456501" lat="59.7210227" lon="10.8399390" version="1" timestamp="2014-12-14T15:09:35Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456502" lat="59.7210365" lon="10.8400982" version="1" timestamp="2014-12-14T15:09:35Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456503" lat="59.7210379" lon="10.8400338" version="1" timestamp="2014-12-14T15:09:35Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456504" lat="59.7210380" lon="10.8399016" version="1" timestamp="2014-12-14T15:09:35Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456505" lat="59.7210384" lon="10.8398784" version="1" timestamp="2014-12-14T15:09:35Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456506" lat="59.7210436" lon="10.8399407" version="1" timestamp="2014-12-14T15:09:35Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456507" lat="59.7210444" lon="10.8399021" version="1" timestamp="2014-12-14T15:09:35Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456508" lat="59.7210875" lon="10.8398824" version="1" timestamp="2014-12-14T15:09:36Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456509" lat="59.7210880" lon="10.8398616" version="1" timestamp="2014-12-14T15:09:36Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456510" lat="59.7211161" lon="10.8398847" version="1" timestamp="2014-12-14T15:09:36Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456511" lat="59.7211166" lon="10.8398639" version="1" timestamp="2014-12-14T15:09:36Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456512" lat="59.7211244" lon="10.8401054" version="1" timestamp="2014-12-14T15:09:36Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456513" lat="59.7211259" lon="10.8400348" version="1" timestamp="2014-12-14T15:09:36Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456514" lat="59.7211272" lon="10.8399730" version="1" timestamp="2014-12-14T15:09:36Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456515" lat="59.7211290" lon="10.8398858" version="1" timestamp="2014-12-14T15:09:36Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456516" lat="59.7211394" lon="10.8400359" version="1" timestamp="2014-12-14T15:09:36Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <node id="3234456517" lat="59.7211407" lon="10.8399741" version="1" timestamp="2014-12-14T15:09:36Z" changeset="27460243" uid="36147" user="Øystein Bjørndal"/>
  <way id="317205476" version="4" timestamp="2015-09-06T12:58:37Z" changeset="33832254" uid="3095942" user="Øystein Bjørndal_import">
    <nd ref="3234456515"/>
    <nd ref="3234456510"/>
    <nd ref="3234456511"/>
    <nd ref="3234456509"/>
    <nd ref="3234456508"/>
    <nd ref="3234456505"/>
    <nd ref="3234456504"/>
    <nd ref="3234456507"/>
    <nd ref="3234456506"/>
    <nd ref="3234456501"/>
    <nd ref="3234456500"/>
    <nd ref="3234456503"/>
    <nd ref="3234456502"/>
    <nd ref="3234456512"/>
    <nd ref="3234456513"/>
    <nd ref="3234456516"/>
    <nd ref="3234456517"/>
    <nd ref="3234456514"/>
    <nd ref="3234456515"/>
    <tag k="amenity" v="kindergarten"/>
    <tag k="building" v="kindergarten"/>
    <tag k="capacity" v="18"/>
    <tag k="contact:phone" v="64877130"/>
    <tag k="max_age" v="5"/>
    <tag k="min_age" v="3"/>
    <tag k="name" v="Spilloppen barnehage"/>
    <tag k="no-barnehage:nsrid" v="1016218"/>
    <tag k="operator" v="Ski Kvinne &amp; Familieforbund"/>
    <tag k="operator:type" v="private"/>
  </way>

</osm>
"""

# Example dictionary
barnehagefakta_no_nbrId1016218 = json.loads('''{"id":"2feddb70-fc82-4227-a476-85b32f79eeb1","alder":"3 - 5","ansatte":{"antallFra":5,"antallTil":9},"eierform":"Privat","basilId":"46979","erAktiv":true,"erBarnehage":true,"erBarnehageEier":false,"erPrivatBarnehage":true,"fylke":{"fylkesnavn":"Akershus","fylkesnummer":"02"},"kommune":{"kommunenavn":"Ski","kommunenummer":"0213"},"kontaktinformasjon":{"postAdresse":{"adresselinje":"H0404 v/Svein Helgerud Midtskogen 4","postnr":"1400","poststed":"SKI"},"besoksAdresse":{"adresselinje":"Kirkeveien 13","postnr":"1400","poststed":"SKI"},"epost":"","url":"","telefon":"64877130"},"koordinatLatLng":[59.7211,10.84],"malform":{"malformType":"B","malformNavn":"Bokmål"},"opprettetDato":"1/1/1990","navn":"Spilloppen barnehage","orgnr":"974195135","nsrId":"1016218","indikatorDataBarnehage":{"antallBarn":18,"antallBarnPerAnsatt":5.9,"andelAnsatteMedBarneOgUngdomsarbeiderfag":0.0,"andelAnsatteMedAnnenPedagogiskUtdanning":0.0,"andelAnsatteBarnehagelarer":40.0,"andelAnsatteMedAnnenBakgrunn":60.0,"andelAnsatteMedPedagogiskUtdanning":40.0,"lekeOgOppholdsarealPerBarn":4.0},"indikatorDataKommune":{"antallBarn":1829,"antallBarnPerAnsatt":6.4,"andelAnsatteMedBarneOgUngdomsarbeiderfag":19.5,"andelAnsatteMedAnnenPedagogiskUtdanning":7.7,"andelAnsatteBarnehagelarer":39.7,"andelAnsatteMedAnnenBakgrunn":33.1,"andelAnsatteMedPedagogiskUtdanning":47.4,"lekeOgOppholdsarealPerBarn":5.2},"kostpenger":180.0,"type":"Ordinær barnehage","pedagogiskProfil":"","apningstidFra":"07:30","apningstidTil":"16:30","oppfyllerPedagognorm":"Oppfyller normen","urlTilSoknadOmBarnehageplass":"http://www.ski.no/Om-kommunen/Organisering/Virksomheter/Barnehagene-i-Ski/#"}''')

class MyTest(unittest.TestCase):
    def setUp(self):
        self.osm_outdated, _ = create_osmtags(barnehagefakta_no_nbrId1016218)
        self.osm_updated, _ = create_osmtags(barnehagefakta_no_nbrId1016218)

        osm = osmapis.OSM.from_xml(reply_way)
        osm_elements = list(update_osm.find_all_nsrid_osm_elements(osm))
        self.assertEqual(len(osm_elements), 1)
        self.osm_element = osm_elements[0]
    def tearDown(self):
        pass

    def test_create_osmtags(self):
        self.assertEqual(self.osm_outdated.tags, self.osm_updated.tags)
        self.assertEqual(self.osm_outdated.attribs['lat'], self.osm_updated.attribs['lat'])
        self.assertEqual(self.osm_outdated.attribs['lon'], self.osm_updated.attribs['lon'])        
        self.assertEqual(self.osm_outdated.tags, {'max_age': '5',
                                                  'amenity': 'kindergarten',
                                                  'capacity': '18',
                                                  'name': u'Spilloppen barnehage',
                                                  'operator:type': 'private',
                                                  'contact:phone': u'64877130',
                                                  'min_age': '3',
                                                  'no-barnehage:nsrid': u'1016218',
                                                  'start_date': '1990-01-01'})

    def test_tags_equal(self):
        action = update_osm.resolve_conflict(self.osm_element, self.osm_outdated, self.osm_updated)
        self.assertEqual(action, True)
        
    def test_tags_added_new_tag(self, value='new_value'):
        '''
        NBR adds a value which is not in osm.
        Should indicate that an auto-update is ok.
        '''
        self.assertFalse('new_tag' in self.osm_updated.tags)
        self.osm_updated.tags['new_tag'] = value

        self.assertTrue('new_tag' not in self.osm_element.tags)
        action = update_osm.resolve_conflict(self.osm_element, self.osm_outdated, self.osm_updated)
        self.assertEqual(action, 'update')
        self.assertTrue('new_tag' in self.osm_element.tags)

    def test_tags_added_building(self, value='new_value'):
        '''
        NBR adds a value which is in osm, and the value is missmatched. 
        Should indicate that a manual intervention is needed
        '''        
        self.assertFalse('new_tag' in self.osm_updated.tags)
        self.osm_updated.tags['building'] = value

        self.assertTrue(self.osm_element.tags['building'], 'kindergarten')
        ret = update_osm.resolve_conflict(self.osm_element, self.osm_outdated, self.osm_updated)
        self.assertFalse(ret)
        self.assertEqual(self.osm_element.tags['building'], 'kindergarten')

    def test_tags_added_building_equal(self):
        '''
        NBR adds a value which is in osm, and the value is the same. 
        This can be ignored, no action needed.
        '''                
        self.assertFalse('new_tag' in self.osm_updated.tags)
        self.osm_updated.tags['building'] = self.osm_element.tags['building']

        self.assertTrue(self.osm_element.tags['building'], 'kindergarten')
        ret = update_osm.resolve_conflict(self.osm_element, self.osm_outdated, self.osm_updated)
        self.assertTrue(ret)
        self.assertEqual(self.osm_element.tags['building'], 'kindergarten')
        
    def test_tags_deleted(self, del_key='contact:phone'):
        '''
        NBR removes a value which is in osm, the outdated value matches the osm value.
        Should indicate that an auto-update is ok.
        '''
        del self.osm_updated.tags[del_key]

        self.assertTrue(del_key in self.osm_element.tags)
        self.assertEqual(self.osm_element.tags[del_key], self.osm_outdated.tags[del_key])
        ret = update_osm.resolve_conflict(self.osm_element, self.osm_outdated, self.osm_updated)
        self.assertFalse(del_key in self.osm_element.tags)
        self.assertEqual(ret, 'update')        

    def test_tags_deleted_ignored(self, del_key='contact:phone'):
        '''
        NBR removes a value which is not in osm.
        This can be ignored, no action needed.
        '''
        del self.osm_updated.tags[del_key]
        del self.osm_element.tags[del_key]
        
        ret = update_osm.resolve_conflict(self.osm_element, self.osm_outdated, self.osm_updated)
        self.assertEqual(ret, True)
        
    def test_tags_deleted_tampered(self, del_key='contact:phone'):
        '''
        NBR removes a value which is in osm, the outdated value does not match the osm value.
        Should indicate that a manual intervention is needed        
        '''
        del self.osm_updated.tags[del_key]
        self.assertTrue(del_key in self.osm_element.tags)        
        self.osm_element.tags[del_key] += 'tampered'

        self.assertNotEqual(self.osm_element.tags[del_key], self.osm_outdated.tags[del_key])        
        ret = update_osm.resolve_conflict(self.osm_element, self.osm_outdated, self.osm_updated)
        self.assertEqual(ret, False)
        
    def test_tags_modified(self, key='contact:phone', value='42'):
        '''
        NBR modifies a value which is in osm, the outdated value matches the osm value
        Should indicate that an auto-update is ok.
        '''
        self.osm_updated.tags[key] = value

        ret = update_osm.resolve_conflict(self.osm_element, self.osm_outdated, self.osm_updated)
        self.assertEqual(self.osm_element.tags[key], value)
        self.assertEqual(ret, 'update')
        
    def test_tags_modified_tampered(self, key='contact:phone', value='42'):
        '''
        NBR modifies a value which is in osm, the outdated value does not match the osm value.
        Should indicate that a manual intervention is needed        
        '''
        self.osm_updated.tags[key] = value
        value_tampered = self.osm_element.tags[key] + 'tampered'
        self.osm_element.tags[key] = value_tampered

        ret = update_osm.resolve_conflict(self.osm_element, self.osm_outdated, self.osm_updated)
        self.assertEqual(self.osm_element.tags[key], value_tampered)
        self.assertEqual(ret, False)
        
    def test_tags_modified_removed(self, key='contact:phone', value='42'):
        '''
        NBR modifies a value which is not in osm,
        Should indicate that a manual intervention is needed        
        '''
        self.osm_updated.tags[key] = value
        del self.osm_element.tags[key]

        ret = update_osm.resolve_conflict(self.osm_element, self.osm_outdated, self.osm_updated)
        self.assertFalse(key in self.osm_element.tags)
        self.assertEqual(ret, False)
