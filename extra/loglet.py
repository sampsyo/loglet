"""Python bindings for the Loglet service."""
import logging
import urllib

BASE_URL = 'http://loglet.radbox.org/'

def log(logid, message, level=0):
    """Post a message to the specified log on Loglet."""
    url = BASE_URL + logid
    params = {
        'message': message,
        'level': level,
    }
    urllib.urlopen(url, urllib.urlencode(params))

class LogletHandler(logging.Handler):
    """A logging handler that sends messages to a Loglet log. Pass the
    Loglet ID as the first parameter to the constructor.
    """
    def __init__(self, logid, level=logging.NOTSET):
        logging.Handler.__init__(self, level)
        self.logid = logid

    def emit(self, record):
        log(self.logid, record.getMessage(), record.levelno)
