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


# Various techniques for running the request asynchronously. 

def threading_apply(func, args=(), kwargs={}):
    """Apply a function in another thread."""
    t = threading.Thread(target=func, args=args, kwargs=kwargs)
    t.start()

ASYNC_FUNCTIONS['threading'] = threading_apply

try:
    import multiprocessing
except ImportError:
    pass
else:
    def multiprocessing_apply(func, args=(), kwargs={}):
        """Apply a function in another process."""
        p = multiprocessing.Process(target=func, args=args, kwargs=kwargs)
        p.start()
    ASYNC_FUNCTIONS['multiprocessing'] = multiprocessing_apply

try:
    import gevent.pool
except ImportError:
    pass
else:
    gevent_pool = gevent.pool.Pool(size=15)
    def gevent_apply(func, args=(), kwargs={}):
        """Apply a function in another green thread."""
        gevent_pool.spawn(func, *args, **kwargs)
    ASYNC_FUNCTIONS['gevent'] = gevent_apply


# Handler for the Python logging standard library module.

class LogletHandler(logging.Handler):
    """A logging handler that sends messages to a Loglet log. Pass the
    Loglet ID as the first parameter to the constructor.
    """
    def __init__(self, logid, level=logging.NOTSET, mode='sync'):
        """Create a new Loglet handler. An ID string for the log must
        be provided. The mode parameter specifies whether log requests
        should be performed asynchronously. Possible values are
        "sync" (blocking request), "threading", "multiprocessing", or
        "gevent".
        """
        logging.Handler.__init__(self, level)
        self.logid = logid
        try:
            self.apply = ASYNC_FUNCTIONS[mode]
        except KeyError:
            async_types = tuple(ASYNC_FUNCTIONS.iterkeys())
            raise ValueError('no such mode ' + repr(mode) + '; ' +
                             'choose one of ' + repr(async_types))

    def emit(self, record):
        args = self.logid, record.getMessage(), record.levelno
        self.apply(log, args)

