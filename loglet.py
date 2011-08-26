import flask
from flask import g, request
import sqlite3
from contextlib import closing
import string
import random
import time
from datetime import datetime

DB_NAME = 'loglet.db'

def random_string(length=16, chars=(string.ascii_letters + string.digits)):
    return ''.join(random.choice(chars) for i in range(length))


app = flask.Flask(__name__)

@app.before_request
def before_request():
    g.db = sqlite3.connect(DB_NAME)
@app.teardown_request
def teardown_request(req):
    g.db.close()

@app.template_filter('timeformat')
def timeformat(ts, fmt='%d-%m-%Y %H:%M:%S'):
    return datetime.fromtimestamp(ts).strftime(fmt)

def init_db():
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


def _id_for_log(longid):
    c = g.db.execute("SELECT id FROM logs WHERE longid = ?", (longid,))
    with closing(c):
        row = c.fetchone()
        if not row:
            RAISE404
        return row[0]

def _messages_for_log(longid):
    logid = _id_for_log(longid)
    c = g.db.execute("SELECT message, time FROM messages WHERE logid = ? "
                     "ORDER BY time DESC",
                     (logid,))
    messages = []
    with closing(c):
        for row in c:
            messages.append({
                'message': row[0],
                'time': row[1]
            })
    return messages


@app.route("/")
def home():
    return flask.render_template('index.html')

@app.route("/new", methods=["POST"])
def newlog():
    longid = random_string()
    with g.db:
        g.db.execute("INSERT INTO logs (longid, name, twitternames) "
                    "VALUES (?, ?, ?)",
                    (longid, 'new log', ''))
    return flask.redirect('/' + longid)

@app.route("/<longid>", methods=["POST", "GET"])
def log(longid):
    if request.method == 'POST':
        # Add to log.
        message = request.form['message']
        try:
            level = request.form['level']
        except KeyError:
            level = 0

        logid = _id_for_log(longid)
        with g.db:
            g.db.execute("INSERT INTO messages (logid, message, time, level)"
                         " VALUES (?, ?, ?, ?)",
                         (logid, message, int(time.time()), level))
        
        return flask.jsonify(success=1)

    else:
        # Show log.
        return flask.render_template('log.html',
                                    messages=_messages_for_log(longid),
                                    longid=longid)

@app.route("/<longid>/txt")
def logtxt(longid):
    outlines = []
    for message in _messages_for_log(longid):
        outlines.append('%i %s' % (message['time'], message['message']))
    text = "\n".join(outlines)
    return flask.Response(text, content_type="text/plain")

@app.route("/<longid>/json")
def logjson(longid):
    return flask.jsonify(log=longid, messages=_messages_for_log(longid))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
