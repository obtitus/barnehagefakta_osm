# Standard python imports
import time
import logging
logger = logging.getLogger('barnehagefakta.nbrId')
# Non-standard imports
import requests
# This project
import file_util

class GentleRequests(requests.Session):
    """Wrapper around the requests library that inserts a delay to avoid
    excessive load on the server.
    NOTE: currently only wraps get() calls."""
    def __init__(self, N_delay=10, delay_seconds=30):
        """For every N_delay requests, delay by delay_seconds"""
        self.N_delay = N_delay
        self.delay_seconds = delay_seconds
        self.previous_request = None
        self.request_counter = 0
        
        super(GentleRequests, self).__init__()

        info = 'Barnehagefakta to Openstreetmap (https://github.com/obtitus/barnehagefakta_osm) '
        self.headers['User-Agent'] = info + self.headers['User-Agent']

    def get(self, *args, **kwargs):
        # ugly? yes, over-complicated? yes, wierd? definitely
        if self.request_counter == 0:
            self.previous_request = time.time()
        elif self.request_counter >= self.N_delay:
            sleep_time = self.delay_seconds - (time.time() - self.previous_request)
            self.request_counter = -1
            if sleep_time > 0:
                logger.info('Sleeping request for %g seconds...', sleep_time)
                time.sleep(sleep_time)
                
        self.request_counter += 1
        
        return super(GentleRequests, self).get(*args, **kwargs)

    def get_cached(self, url, cache_filename, old_age_days=30):
        cached, outdated = file_util.cached_file(cache_filename, old_age_days)
        if cached is not None and not(outdated):
            return cached

        try:
            r = self.get(url)
        except requests.ConnectionError as e:
            logger.error('Could not connect to %s, try again later? %s', url, e)
            return None

        logger.info('requested %s, got %s', url, r)
        if r.status_code == 200:
            ret = r.content
            file_util.write_file(cache_filename, ret)
            return ret
        else:
            logger.error('Invalid status code %s', r.status_code)
            return None
