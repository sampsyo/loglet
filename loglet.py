import flask
from flask import g, request
import sqlite3
from contextlib import closing
import string
import random
import time
from datetime import datetime
from werkzeug.contrib.atom import AtomFeed
import urlparse


# Constants.

DB_NAME = 'loglet.db'
MIN_LEVEL = 0
MAX_LEVEL = 100
MAX_MSG_LENGTH = 4096
LEVEL_WARN = 30
LEVEL_ERROR = 40
MAX_MESSAGES = 512
DEBUG = False


# Utilities.

def random_string(length=16, chars=(string.ascii_letters + string.digits)):
    """Generate a string of random characters."""
    return ''.join(random.choice(chars) for i in range(length))

def abs_url(*args, **kwargs):
    """Like url_for, but gives an absolute URL."""
    return urlparse.urljoin(request.url_root, flask.url_for(*args, **kwargs))


# Application setup.

app = flask.Flask(__name__)

# Connection to SQLite database.
@app.before_request
def before_request():
    g.db = sqlite3.connect(DB_NAME)
@app.teardown_request
def teardown_request(req):
    g.db.close()

@app.template_filter('timeformat')
def timeformat(ts, fmt='%Y-%m-%d %H:%M:%S'):
    """Format a UNIX timestamp as a string using a strftime format
    template.
    """
    return datetime.fromtimestamp(ts).strftime(fmt)

@app.template_filter('levelname')
def levelname(level):
    """Returns a short string summarizing and integer level. Used for
    CSS classes to style elements according to log severity level.
    """
    if level >= LEVEL_ERROR:
        return 'error'
    elif level >= LEVEL_WARN:
        return 'warning'
    else:
        return 'debug'

# Expose constants to templates.
app.jinja_env.globals.update({
    'min_level': MIN_LEVEL,
    'max_level': MAX_LEVEL,
    'max_msg_length': MAX_MSG_LENGTH,
    'max_messages': MAX_MESSAGES,
})

@app.errorhandler(404)
def notfound(error):
    return flask.render_template('notfound.html'), 404
@app.errorhandler(500)
def servererror(error):
    return flask.render_template('error.html'), 500

def init_db():
    """Initialize the database schema if needed."""
    with closing(sqlite3.connect(DB_NAME)) as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY,
                longid TEXT UNIQUE,
                name TEXT,
                twitternames TEXT
            );
            CREATE INDEX IF NOT EXISTS loglongid ON logs (longid);
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                logid INTEGER,
                message TEXT,
                time INTEGER,
                level INTEGER
            );
            CREATE INDEX IF NOT EXISTS msglog ON messages (logid);
        """)


# Query helpers.

def _id_for_log(longid):
    c = g.db.execute("SELECT id FROM logs WHERE longid = ?", (longid,))
    with closing(c):
        row = c.fetchone()
        if not row:
            flask.abort(404)
        return row[0]

def _messages_for_log(longid):
    logid = _id_for_log(longid)
    c = g.db.execute("SELECT message, time, level FROM messages "
                     "WHERE logid = ? ORDER BY time DESC",
                     (logid,))
    messages = []
    with closing(c):
        for row in c:
            messages.append({
                'message': row[0],
                'time': row[1],
                'level': row[2]
            })
    return messages


# Views.

@app.route("/")
def home():
    """Front page splash."""
    return flask.render_template('index.html')

@app.route("/new", methods=["POST"])
def newlog():
    """Make a new log and redirect to its URL."""
    longid = random_string()
    with g.db:
        g.db.execute("INSERT INTO logs (longid, name, twitternames) "
                    "VALUES (?, ?, ?)",
                    (longid, 'new log', ''))
    return flask.redirect('/' + longid)

@app.route("/<longid>", methods=["POST", "GET"])
def log(longid):
    """View or add to a log."""
    if request.method == 'POST':
        # Add to log.
        message = request.form['message']

        try:
            level = request.form['level']
        except KeyError:
            level = MIN_LEVEL
        try:
            level = int(level)
        except ValueError:
            level = MIN_LEVEL
        if level < MIN_LEVEL:
            level = MIN_LEVEL
        elif level > MAX_LEVEL:
            level = MAX_LEVEL

        logid = _id_for_log(longid)
        with g.db:
            # Add new message.
            g.db.execute("INSERT INTO messages (logid, message, time, level) "
                         "VALUES (?, ?, ?, ?)",
                         (logid, message, int(time.time()), level))
            # Drop old messages.
            g.db.execute("DELETE FROM messages WHERE id IN (SELECT id FROM "
                         "messages WHERE logid = ? ORDER BY time DESC "
                         "LIMIT -1 OFFSET ?)",
                         (logid, MAX_MESSAGES))
        
        return flask.jsonify(success=1)

    else:
        # Show log.
        return flask.render_template('log.html',
                                    messages=_messages_for_log(longid),
                                    longid=longid)

@app.route("/<longid>/txt")
def logtxt(longid):
    """Plain-text log representation."""
    outlines = []
    for message in _messages_for_log(longid):
        outlines.append('%i %i %s' %
                        (message['time'], message['level'], message['message']))
    text = "\n".join(outlines)
    return flask.Response(text, content_type="text/plain")

@app.route("/<longid>/json")
def logjson(longid):
    """JSON log representation."""
    return flask.jsonify(log=longid, messages=_messages_for_log(longid))

@app.route("/<longid>/feed")
def logfeed(longid):
    """Atom feed for a log."""
    logurl = abs_url('log', longid=longid)
    feed = AtomFeed('Loglet Log %s' % longid,
                    feed_url=request.url,
                    url=logurl)
    for message in _messages_for_log(longid):
        pubtime = datetime.fromtimestamp(message['time'])
        feed.add('%i: %s' % (message['level'], message['message'][:128]),
                 '<pre>%s</pre>' % message['message'],
                 content_type='html',
                 url=logurl,
                 published=pubtime,
                 updated=pubtime,
                 author='Loglet')
    return feed.get_response()


# Debug server.

if __name__ == '__main__':
    init_db()
    app.run(debug=DEBUG)
