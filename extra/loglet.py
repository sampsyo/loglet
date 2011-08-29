"""Python bindings for the Loglet service."""
import logging
import urllib
import threading

BASE_URL = 'http://loglet.radbox.org/'
ASYNC_FUNCTIONS = {'sync': apply}

def log(logid, message, level=0):
    """Post a message to the specified log on Loglet."""
    url = BASE_URL + logid
    params = {
        'message': message,
        'level': level,
    }
    urllib.urlopen(url, urllib.urlencode(params))

def threading_apply(object, args=(), kwargs={}):
    """Apply a function in another thread."""
    t = threading.Thread(target=object, args=args, kwargs=kwargs)
    t.start()

ASYNC_FUNCTIONS['threading'] = threading_apply

try:
    import multiprocessing
except ImportError:
    pass
else:
    def multiprocessing_apply(object, args=(), kwargs={}):
        """Apply a function in another process."""
        p = multiprocessing.Process(target=object, args=args, kwargs=kwargs)
        p.start()
    ASYNC_FUNCTIONS['multiprocessing'] = multiprocessing_apply

try:
    import gevent
except ImportError:
    pass
else:
    def gevent_apply(object, args=(), kwargs={}):
        """Apply a function in another green thread."""
        gevent.spawn(object, *args, **kwargs)
    ASYNC_FUNCTIONS['gevent'] = gevent_apply

class LogletHandler(logging.Handler):
    """A logging handler that sends messages to a Loglet log. Pass the
    Loglet ID as the first parameter to the constructor.
    """
    def __init__(self, logid, level=logging.NOTSET, async=None):
        logging.Handler.__init__(self, level)
        self.logid = logid
        try:
            self.apply = ASYNC_FUNCTIONS[async or 'sync']
        except KeyError:
            async_types = tuple(ASYNC_FUNCTIONS.iterkeys())
            raise ValueError(repr(async) + ' is unsupported async type; '
                             'choose one in ' + repr(async_types))

    def emit(self, record):
        args = self.logid, record.getMessage(), record.levelno
        self.apply(log, args)

