#!/usr/bin/env python
# -*- coding: utf8

import re
import logging
logger = logging.getLogger('barnehagefakta.name_cleanup')

def name_cleanup(name, log_filehandle=None):
    u"""Attempt at sanitizing the name from ssr by mainly forcing sane capitalization and removing company designations AS/SA/...
    Doctest:
    >>> name_cleanup('')
    ''
    >>> name_cleanup('Hei')
    'Hei'
    >>> name_cleanup('Hei ')
    'Hei'
    >>> name_cleanup('Frelsesarmeens Barnehager Avd Regnbuen')
    'Frelsesarmeens barnehager avd. Regnbuen'
    >>> name_cleanup('Frelsesarmeens Barnehagene Avd Regnbuen')
    'Frelsesarmeens barnehagene avd. Regnbuen'
    >>> name_cleanup('Frelsesarmeens Barnehage Avd Regnbuen')
    'Frelsesarmeens barnehage avd. Regnbuen'
    >>> name_cleanup('Vardobaiki AS Markomanak barnehage')
    'Vardobaiki Markomanak barnehage'
    >>> name_cleanup('hei barnehageenhet')
    'Hei barnehageenhet'
    >>> name_cleanup('hei NaturBarnehage')
    'Hei naturbarnehage'
    >>> name_cleanup('hei Oppvekstsenter')
    'Hei oppvekstsenter'
    >>> name_cleanup('hei familiebarnehage')
    'Hei familiebarnehage'
    >>> print(name_cleanup(u'Normisjon Lillestrøm Åpen Barnehage')) # utf8 doctest-workaround: print(...)
    Normisjon Lillestrøm åpen barnehage
    >>> print(name_cleanup(u'Foo Gård'))
    Foo gård
    >>> print(name_cleanup(u'Foo Gårdsbarnehage'))
    Foo gårdsbarnehage
    >>> name_cleanup('Lykketrollet Familiebarnehage Avd Saturnveien')
    'Lykketrollet familiebarnehage avd. Saturnveien'
    >>> name_cleanup('foo Menighet ')
    'Foo menighet'
    >>> print(name_cleanup(u'LinnÉa'))
    Linnéa
    >>> name_cleanup('Foo Idrettsbarnehage')
    'Foo idrettsbarnehage'
    >>> name_cleanup('Foo fus SfO i / Ii Kfum kFuK')
    'Foo FUS SFO I / II KFUM KFUK'
    >>> name_cleanup('Hei montessori')
    'Hei Montessori'
    >>> name_cleanup('Hem barnehage V/sidsel Berg Sjulstad')
    'Hem barnehage Sidsel Berg Sjulstad'
    >>> name_cleanup('Hei Familiebarnehage Ved Tove Baa')
    'Hei familiebarnehage Tove Baa'
    >>> name_cleanup('Nlm Hei BaRnehage')
    'NLM Hei barnehage'
    >>> name_cleanup("Nlm Barnehagene AS Avd Tryggheim Barnehage Halden")
    'NLM barnehagene avd. Tryggheim barnehage Halden'
    >>> name_cleanup('Lian Naturbarnehage')
    'Lian naturbarnehage'
    >>> name_cleanup('Slettebakken Menighets barnehage AS')
    'Slettebakken menighets barnehage'
    >>> print(name_cleanup(u'Tiriltoppen barnehage Nøtterøy AS'))
    Tiriltoppen barnehage Nøtterøy
    """
    #name = name.decode('utf8')
    old_name = name
    
    name = name.strip()
    if name == '':
        return ''

    # Replace shorthands
    barnehage_shorthands = ('Bhg', 'Barne')
    for short in barnehage_shorthands:
        reg1 = re.search('([\s]%s$)' % short, name, flags=re.IGNORECASE|re.UNICODE)
        reg2 = re.search('([\s]%s[\s])' % short, name, flags=re.IGNORECASE|re.UNICODE)
        if reg1:
            name = name.replace(reg1.group(1), 'barnehage')
        if reg2:
            name = name.replace(reg2.group(1), 'barnehage')
    
    # remove AS, Sa
    for company_short in('AS', 'Sa', 'A/s', 'Da', 'Ba', 'Ans', 'Ltd', 'Ikb', 'Ved', 'Si'):
        # company_short at end of string with space in front:
        reg1 = re.search('([\s]%s$)' % company_short, name, flags=re.IGNORECASE|re.UNICODE)
        # company_short with spaces on both sides:
        reg2 = re.search('([\s]%s[\s])' % company_short, name, flags=re.IGNORECASE|re.UNICODE)
        if reg1:
            name = name.replace(reg1.group(1), '')
        if reg2:
            name = name.replace(reg2.group(1), ' ')
        # name = name.replace(company_short, '')
        # name = name.replace(company_short.lower(), '')

    # Fixme: learn reg-replace?
    # lowercase for barnehageenhet, naturbarnehage, oppvekstsenter, familiebarnehage, ...
    for reg in re.finditer('([\w]*barnehage[\w]*)', name, flags=re.IGNORECASE|re.UNICODE):
        name = name.replace(reg.group(1), reg.group(1).lower())

    # Lower case for a bunch of other cases
    for case in ('oppvekstsenter', 'menighet[s]?', 'barnehave', u'åpen', 'grendehus',
                 'terrasse', u'gård', 'privat', 'kultur', 'skole', 'skoleordning',
                 'natur', 'kirke[s]?', 'kommunale', u'Oppvekstområde', 'Oppvekst',
                 'Of', 'musikk', 'familie'):
        reg = re.search('(%s)' % case, name, flags=re.IGNORECASE|re.UNICODE)
        if reg:
            name = name.replace(reg.group(1), reg.group(1).lower())
        
    # avd. for Avd, avd
    reg = re.search(' (avd[.]?) ', name, flags=re.IGNORECASE|re.UNICODE)
    if reg:
        name = name.replace(reg.group(1), "avd.")

    # avd. for Avdelig
    reg = re.search(' (Avdeling) ', name, flags=re.IGNORECASE|re.UNICODE)
    if reg:
        name = name.replace(reg.group(1), "avd.")
        
    new_name = []
    abbrevs = ('fus', 'sfo', 'nlm', 'kfum', 'kfuk', 'hf')
    capitalize = ('montessori', 'steinerbarnehage')
    remove = ('Ved', )
    for word in name.split():
        word_low = word.lower()
        if word_low in abbrevs:
            word = word.upper()
        elif word_low in capitalize:
            word = word.capitalize()
        elif word_low.startswith('v/'):
            word = word[2:].capitalize()
        elif word in remove:
            continue
        else:
            word = word[0] + word[1:].lower() # e.g. LinnÉa -> Linnéa
        new_name.append(word)

    if new_name[0].lower() not in abbrevs:
        new_name[0] = new_name[0].capitalize()
    
    name = " ".join(new_name)
    #name = name[0].upper() + name[1:]

    name = name.replace('i / Ii', 'i / Ii'.upper())

    #print(old_name, name)
    if name != old_name:
        logger.debug('name cleanup %s -> %s', old_name, name)

    if log_filehandle is not None and old_name != name:
        log_filehandle.write('"%s", "%s"\n' % (old_name, name))
    return name

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    
