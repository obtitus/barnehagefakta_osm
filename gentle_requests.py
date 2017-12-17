# Standard python imports
import time
import datetime
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
    def __init__(self, N_delay=10, delay_seconds=30, retry_connection_error_hours=24,
                 info = 'Barnehagefakta to Openstreetmap (https://github.com/obtitus/barnehagefakta_osm) '):
        """For every N_delay requests, delay by delay_seconds, if connection failure, retry for retry_connection_error_hours"""
        self.N_delay = N_delay
        self.delay_seconds = delay_seconds
        self.previous_request = None
        self.request_counter = 0
        self.retry_connection_error_hours = retry_connection_error_hours
        
        super(GentleRequests, self).__init__()
        
        self.headers['User-Agent'] = info + self.headers['User-Agent']

    def get(self, url, *args, **kwargs):
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

        # now retry until we do not get a ConnectionError
        first_request = time.time()
        delta = 0
        while delta < 3600*self.retry_connection_error_hours:
            try:
                return super(GentleRequests, self).get(url, *args, **kwargs)
            except (requests.ConnectionError, requests.ReadTimeout) as e:
                delta = time.time() - first_request

                # decide on severity:
                logger_lvl = logging.DEBUG
                if delta > 60:
                    logger_lvl = logging.INFO
                if delta > 60*5:
                    logger_lvl = logging.WARNING
                if delta > 60*60:
                    logger_lvl = logging.ERROR
                # log
                logger.log(logger_lvl, 'Could not connect to %s, trying again in %s: %s',
                           url, datetime.timedelta(seconds=delta), e)
                # linear backoff
                time.sleep(delta)

        # try a last time
        return super(GentleRequests, self).get(url, *args, **kwargs)

    def get_cached(self, url, cache_filename, old_age_days=30):
        cached, outdated = file_util.cached_file(cache_filename, old_age_days)
        if cached is not None and not(outdated):
            return cached

        try:
            r = self.get(url)
        except requests.ConnectionError as e:
            logger.error('Could not connect to %s, try again later? %s', url, e)
            return None

        logger.info('requested %s %s, got %s', url, cache_filename, r)
        if r.status_code == 200:
            ret = r.content
            file_util.write_file(cache_filename, ret)
            return ret
        else:
            logger.error('Invalid status code %s', r.status_code)
            return None
