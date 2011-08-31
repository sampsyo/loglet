import flask
from flask import g, request
import sqlite3
from contextlib import closing
import string
import random
import time
import datetime
from werkzeug.contrib.atom import AtomFeed


# Constants.

DB_NAME = 'loglet.db'
MIN_LEVEL = 0
MAX_LEVEL = 100
MAX_MSG_LENGTH = 4096
LEVEL_WARN = 30
LEVEL_ERROR = 40
MAX_MESSAGES = 512
TIME_ZONES = [
    (-12.0, "Eniwetok, Kwajalein"),
    (-11.0, "Midway Island, Samoa"),
    (-10.0, "Hawaii"),
    (-9.0, "AKST"),
    (-8.0, "PST, AKDT"),
    (-7.0, "MST, PDT"),
    (-6.0, "CST, MDT, Mexico City"),
    (-5.0, "EST, CDT, Bogota, Lima"),
    (-4.0, "EDT, Atlantic Time, Caracas, La Paz"),
    (-3.5, "Newfoundland"),
    (-3.0, "Brazil, Buenos Aires, Georgetown"),
    (-2.0, "Mid-Atlantic"),
    (-1.0, "Azores, Cape Verde Islands"),
    (+0.0, "Western Europe Time, London, Lisbon, Casablanca"),
    (+1.0, "Brussels, Copenhagen, Madrid, Paris"),
    (+2.0, "Kaliningrad, South Africa"),
    (+3.0, "Baghdad, Riyadh, Moscow, St. Petersburg"),
    (+3.5, "Tehran"),
    (+4.0, "Abu Dhabi, Muscat, Baku, Tbilisi"),
    (+4.5, "Kabul"),
    (+5.0, "Ekaterinburg, Islamabad, Karachi, Tashkent"),
    (+5.5, "Bombay, Calcutta, Madras, New Delhi"),
    (+5.75, "Kathmandu"),
    (+6.0, "Almaty, Dhaka, Colombo"),
    (+7.0, "Bangkok, Hanoi, Jakarta"),
    (+8.0, "Beijing, Perth, Singapore, Hong Kong"),
    (+9.0, "Tokyo, Seoul, Osaka, Sapporo, Yakutsk"),
    (+9.5, "Adelaide, Darwin"),
    (+10.0, "Eastern Australia, Guam, Vladivostok"),
    (+11.0, "Magadan, Solomon Islands, New Caledonia"),
    (+12.0, "Auckland, Wellington, Fiji, Kamchatka"),
]


# Utilities.

def random_string(length=16, chars=(string.ascii_letters + string.digits)):
    """Generate a string of random characters."""
    return ''.join(random.choice(chars) for i in range(length))


# Application setup.

app = flask.Flask(__name__)
app.debug = True

# Connection to SQLite database.
@app.before_request
def before_request():
    g.db = sqlite3.connect(DB_NAME)
@app.teardown_request
def teardown_request(req):
    g.db.close()

@app.template_filter('timeformat')
def timeformat(ts, tzoffset=0, fmt='%Y-%m-%d %H:%M:%S'):
    """Format a UNIX timestamp as a string using a strftime format
    template. tz is a time zone offset in hours.
    """
    dt = datetime.datetime.utcfromtimestamp(ts)
    dt += datetime.timedelta(hours=tzoffset)
    return dt.strftime(fmt)

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

@app.template_filter('tzrep')
def tzrep(tzoffset):
    """Given a timezone offset, return a short string depicting the
    offset from UTC.
    """
    if tzoffset == 0.0:
        return "UTC"

    offset_hours = int(tzoffset)
    offset_mins = abs(tzoffset - offset_hours) * 60
    offset_str = '%i:%02i' % (offset_hours, offset_mins)
    if tzoffset > 0.0:
        offset_str = "+" + offset_str
    return "UTC " + offset_str

# Expose constants to templates.
app.jinja_env.globals.update({
    'min_level': MIN_LEVEL,
    'max_level': MAX_LEVEL,
    'max_msg_length': MAX_MSG_LENGTH,
    'max_messages': MAX_MESSAGES,
    "time_zones": TIME_ZONES,
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
                     "WHERE logid = ? ORDER BY time DESC, id DESC",
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
    app.logger.debug('created: %s'% longid)
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
                         "messages WHERE logid = ? ORDER BY time DESC, id DESC "
                         "LIMIT -1 OFFSET ?)",
                         (logid, MAX_MESSAGES))
        
        return flask.jsonify(success=1)

    else:
        # Show log.
        try:
            tzoffset = float(request.args['tzoffset'])
        except (KeyError, ValueError):
            tzoffset = 0.0

        return flask.render_template('log.html',
                                     messages=_messages_for_log(longid),
                                     longid=longid,
                                     tzoffset=tzoffset)

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
    logurl = flask.url_for('log', longid=longid, _external=True)
    feed = AtomFeed('Loglet Log %s' % longid,
                    feed_url=request.url,
                    url=logurl)
    for message in _messages_for_log(longid):
        pubtime = datetime.datetime.utcfromtimestamp(message['time'])
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
    app.run()
