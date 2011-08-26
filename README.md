Loglet
======

[Loglet][loglet] is a tiny tool for keeping tabs on long-running processes. Send
log messages to Loglet using a simple `POST` request and then view them in your
browser or subscribe to an Atom feed.

Head over to the site and create a new log. Then send `POST` requests to add
messages:

    curl -d message=hello http://loglet.radbox.org/LOGID

Or use the included [Python logging handler][handler] to hook into your existing
logs:

    import logging
    import loglet
    log = logging.getLogger('mylog')
    log.addHandler(loglet.LogletHandler('LOGID'))
    log.error('something horrible has happened')

[loglet]: http://loglet.radbox.org/
[handler]: https://github.com/sampsyo/loglet/blob/master/extra/loglet.py


About
-----

Loglet is by [Adrian Sampson][adrian] ([@samps][twitter]) and depends on
[Python][python], [Flask][flask], and [SQLite][sqlite]. It includes the
[Bootstrap][bootstrap] compiled CSS framework.

The code is made available under the [MIT license][mit].

[adrian]: http://www.cs.washington.edu/homes/asampson/
[twitter]: http://twitter.com/samps/
[python]: http://python.org/
[flask]: http://flask.pocoo.org/
[sqlite]: http://www.sqlite.org/
[bootstrap]: http://twitter.github.com/bootstrap/
[mit]: http://www.opensource.org/licenses/mit-license.php
