# Database switched from having nsrId to using orgnr, this script helps with this conversion.
import os
import re
import json
import subprocess
from glob import glob

from utility_to_osm import file_util

if __name__ == '__main__':
    data_dir = 'data' #'barnehagefakta_osm_data/data'
    nsrId_to_orgnr_filename = 'nsrId_to_orgnr.json'

    if False:
        # Done once, on a old dump of the database, to get mapping from nsrId to orgnr
        nsrId_to_orgnr = dict()
        for kommune_nr in os.listdir(data_dir):
            folder = os.path.join(data_dir, kommune_nr)
            if os.path.isdir(folder):
                print(folder)

                count = 0
                for filename in glob(os.path.join(folder, 'barnehagefakta_no_nbrId*.json')):
                    content = file_util.read_file(filename)
                    if content == '404':
                        # cleanup
                        os.remove(filename)
                        continue

                    dct = json.loads(content)
                    nsrId = dct['nsrId']
                    orgnr = dct['orgnr']
                    if nsrId in nsrId_to_orgnr and nsrId_to_orgnr[nsrId] != orgnr:
                        raise ValueError('Duplicate key %s, %s != %s' % (nsrId, nsrId_to_orgnr[nsrId], orgnr))

                    nsrId_to_orgnr[nsrId] = orgnr
                    count += 1
                print('Found', count)

        with open(nsrId_to_orgnr_filename, 'w') as f:
            json.dump(nsrId_to_orgnr, f)

    content = file_util.read_file(nsrId_to_orgnr_filename)
    nsrId_to_orgnr = json.loads(content)
    
    if True:
        # Rename files
        for kommune_nr in os.listdir(data_dir):
            folder = os.path.join(data_dir, kommune_nr)
            if os.path.isdir(folder):
                print(folder)

                count = 0
                for filename in glob(os.path.join(folder, 'barnehagefakta_no_nbrId*.json')):
                    reg = re.search('barnehagefakta_no_nbrId(\d+)', filename)
                    if reg:
                        nbrId = reg.group(1)
                        try:
                            orgnr = nsrId_to_orgnr[nbrId]
                        except KeyError as e:
                            content = file_util.read_file(filename)
                            print('ERROR', repr(e), filename, content)
                            if content == '404':
                                os.remove(filename)
                            continue
                            
                        new_filename = filename.replace('barnehagefakta_no_nbrId%s' % nbrId,
                                                        'barnehagefakta_no_orgnr%s' % orgnr)

                        subprocess.run(['git', 'mv', filename, new_filename])
                        # if the file is still there, probably not version controlled
                        if os.path.exists(filename):
                            os.rename(filename, new_filename)
