''' Utility file functions'''
import os
import time
import shutil

import logging
logger = logging.getLogger('barnehagefakta.file_util')

def rename_file(filename, append):
    """Rename the file by appending, append (while keeping the file-extension). 
    IOError is raised if this would cause an overwrite."""
    name, ext = os.path.splitext(filename)
    new_filename = name + append + ext
    if os.path.exists(new_filename):
        raise IOError('Filename "%s" already exists', filename)
    logger.info('Renaming "%s" -> "%s"', filename, new_filename)
    
    shutil.move(filename, new_filename)

def create_dirname(filename):
    """Given a filename, assures the directory exist"""
    dirname = os.path.dirname(filename)
    if not(os.path.exists(dirname)):
        os.mkdir(dirname)
    return filename

def read_file(filename):
    with open(filename, 'r') as f:
        return f.read()

def write_file(filename, content):
    """Write content to filename, tries to create dirname if the folder does not exist."""
    create_dirname(filename)
    with open(filename, 'w') as f:
        return f.write(content)

def file_age(filename):
    fileChanged = os.path.getmtime(filename)
    now = time.time()
    age = (now - fileChanged)/(60*60*24) # age of file in days
    return age

def cached_file(filename, old_age_days):
    """ Returns: (content, outdated)
    Returns a tuple of file content (if the file exists) 
    and a boolean for file age older than old_age_days.
    If the file does not exists, (None, False) is returned.
    """
    if os.path.exists(filename):
        age = file_age(filename)
        content = read_file(filename)
        return content, age > old_age_days
    else:
        return None, True
