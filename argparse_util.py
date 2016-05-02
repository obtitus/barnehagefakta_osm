import argparse
import logging

def get_parser(description, **kwargs):
    return argparse.ArgumentParser(description=description, **kwargs)

def add_verbosity(parser, default=logging.DEBUG):
    ''' inspired by http://stackoverflow.com/a/20663028
    Adds command line arguments for controlling logging level
    '''
    parser.add_argument('-d', '--debug', help="Print lots of debugging statements",
                        action="store_const", dest="loglevel", const=logging.DEBUG,
                        default=default)
    parser.add_argument('-v', '--verbose', help="Be verbose",
                        action="store_const", dest="loglevel", const=logging.INFO)
    parser.add_argument('-q', '--quiet', help="Suppress non-warning messages.",
                        action="store_const", dest="loglevel", const=logging.WARNING)
    parser.add_argument('-s', '--silent', help="Suppress non-error messages.",
                        action="store_const", dest="loglevel", const=logging.ERROR)
    
