# standard imports
import os
import json
import time
from datetime import datetime, timedelta
import logging
logger = logging.getLogger('barnehagefakta.email_verification')

# This project
from mypasswords import mailboxlayer_access_key
from utility_to_osm import file_util
from utility_to_osm import gentle_requests
request_session = gentle_requests.GentleRequests()

N_max = 25                     # avoid getting close to the mailbox limit
# global N_requests
# N_requests = 0                  # fixme: persist on file.

class UsageLimitReachedException(Exception):
    pass

def call_mailbox(email, N_requests_cache=None):
    if N_requests_cache is None: N_requests_cache = dict()
    
    url = 'https://apilayer.net/api/check'
    url += '?access_key=%s' % mailboxlayer_access_key
    #url += '&smtp=1'
    url += '&email=%s' % email

    today = datetime.now()
    try:
        date_str, N_requests = N_requests_cache['N_requests_today']
        date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S') # from string
    except KeyError:
        date, N_requests = today, 0
    
    if today - date >= timedelta(days=1):
        logger.info('Resetting N_requests_today, from %s to 0', N_requests)
        N_requests = 0          # reset
        date = today
    else:
        N_requests += 1
        # keep date!
    
    if N_requests >= N_max:
        raise UsageLimitReachedException('Used all %s requests for today' % N_max)
        
    r = request_session.get(url)
    logger.info('requested %s, got %s', url, r)

    date_str = date.strftime('%Y-%m-%dT%H:%M:%S') # to string
    N_requests_cache['N_requests_today'] = (date_str, N_requests)
    
    if r.status_code == 200:
        ret = r.content
        return ret
    else:
        logger.error('Invalid status code %s', r.status_code)
        return None

def mailbox_check_valid(email, **kwargs):
    """Return True if https://mailboxlayer.com/ says the email is valid, False if invalid 
    and unkown for either:
    - Too many requests
    - Error contacting mailboxlayer
    - Invalid status code from mailbox.
    May raise UsageLimitReachedException"""
    ret = call_mailbox(email, **kwargs)

    if ret == None:
        logger.info('call_mailbox failed, got None')
        return 'unknown'
    
    dct = json.loads(ret)
    
    if 'success' in dct and dct['success'] is False:
        logger.info('call_mailbox failed, success False and %s', dct)
        return 'unknown'
    
    for key in ('format_valid', 'mx_found'): # , 'smtp_check'
        if not(key in dct):
            logger.warning('call_mailbox(%s) failed, key %s not found, %s. Breaking',
                           email, key, dct)
            return False
        elif dct[key] is False:
            logger.warning('call_mailbox(%s) says invalid, key %s = False, %s. Breaking',
                           email, key, dct)
            return False
        else:
            pass

    return True

def mailbox_check_valid_cached(email, email_cache_filename):
    #   uses a dictionary 'database' email_cache where key is email-addr. and value is tuple with
    # - last checked
    # - valid with the possible values: [True, False, unkown]
    try:
        with open(email_cache_filename, 'r') as f:
            email_cache = json.load(f)
    except (IOError, ValueError):
        email_cache = dict()
    
    today = datetime.now()
    valid = 'recheck'
    if email in email_cache:
        last_checked, valid = email_cache[email]
        last_checked = datetime.strptime(last_checked, '%Y-%m-%dT%H:%M:%S')
        age = today - last_checked
        assert valid in (True, False, 'unknown'), 'did not expecte valid = "%s"' % valid
        
        if valid == True and age >= timedelta(days=365): # was True a year ago, best check again.
            valid = 'recheck'
        elif valid in (False, 'unkown') and age >= timedelta(days=60): # check errors more often, in case the error is with mailbox.
            valid = 'recheck'
        else:                   # all ok, use valid as is
            return valid

    
    try:
        valid = mailbox_check_valid(email, N_requests_cache=email_cache)
        # if valid in (False, 'unkown'):
        #     time.sleep(10)
        #     valid2 = mailbox_check_valid(email, N_requests_cache=email_cache)
        #     time.sleep(10)
        #     valid3 = mailbox_check_valid(email, N_requests_cache=email_cache)
            
        #     if valid == valid2 and valid == valid3:
        #         valid = valid2  # ok, 'truly' is False
        #     else:
        #         logger.warning('inconsistent mailbox answer %s, %s, %s', valid, valid2, valid3)
        #         return 'recheck'
                
        today_str = today.strftime('%Y-%m-%dT%H:%M:%S')
        email_cache[email] = (today_str, valid)

        with open(email_cache_filename, 'w') as f:
            json.dump(email_cache, f)

    except UsageLimitReachedException as e:
        logger.info('call_mailbox failed %s', e)
        valid = 'recheck'

    return valid

if __name__ == '__main__':
    print(mailbox_check_valid('obtitus@gmail.com'))
