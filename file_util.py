import os
import time

''' Utility file functions'''
def read_file(filename):
    with open(filename, 'r') as f:
        return f.read()

def write_file(filename, content):
    """Write content to filename, tries to create dirname if the folder does not exist."""
    dirname = os.path.dirname(filename)
    if not(os.path.exists(dirname)):
        os.mkdir(dirname)
    
    with open(filename, 'w') as f:
        return f.write(content)

def file_age(filename):
    fileChanged = os.path.getmtime(filename)
    now = time.time()
    age = (now - fileChanged)/(60*60*24) # age of file in days
    return age

def cached_file(filename, old_age_days):
    """Returns file content if the file exists and is not older than old_age_days"""
    if os.path.exists(filename):
        age = file_age(filename)
        if age < old_age_days:
            return read_file(filename)
    return None
