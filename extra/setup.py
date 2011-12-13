"""
Loglet
======

Loglet_ is a tiny tool for keeping tabs on long-running processes.
Send log messages to Loglet using a simple ``POST`` request and then view
them in your browser or subscribe to an Atom feed.

This Python package provides a small client library of Loglet.  You can
creates a new loglet simply by this and send messages by using standard
``logging`` interface.  For example::

    import logging
    from loglet import LogletHandler

    logger = logging.getLogger(__name__)
    loglet = LogletHandler(mode='threading')
    logger.addHandler(loglet)
    logger.setLevel(logging.DEBUG)

    logger.info('hello')
    logger.error('something horrible has happened')

If you have a loglet already, you can specify logid explicitly::

    loglet = LogletHandler('2LNbYgNEAaezJduj')

There are 4 types of sync/async modes:

``'sync'`` (default)
   Simply sends all logs synchronously.  It can affect serious inefficiency
   to your application.

``'threading'``
   Sends all logs asynchronously by using standard ``threading`` module.
   Threads are rich and heavy to use for just input/output.

``'multiprocessing'``
   Sends all logs asynchronously by using standard ``multiprocessing`` module.
   It requires to use Python 2.6 or higher.  It forks for every message
   internally.

``'gevent'``
   Sends all logs asynchronously by greenlet (coroutine).  It requires
   to install gevent_.  Most efficient way though additional dependency is
   required.

.. _Loglet: http://loglet.radbox.org/
.. _gevent: http://gevent.org/

"""
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from loglet import __version__


setup(name='Loglet',
      version=__version__,
      py_modules=['loglet'],
      scripts=['loglet.sh'],
      author='Adrian Sampson',
      author_email='adrian' '@' 'radbox.org',
      url='http://loglet.radbox.org/',
      description='The Python client library for Loglet',
      long_description=__doc__,
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2 :: Only',
        'Topic :: System :: Logging',
      ])

