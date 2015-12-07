# Standard python imports
import time
import logging
logger = logging.getLogger('barnehagefakta.nbrId')
# Non-standard imports
import requests

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
