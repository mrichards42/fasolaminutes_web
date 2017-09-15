#!/usr/bin/env python
# encoding: utf-8

import os
from flask import Flask, g, request, render_template
from sassutils.wsgi import SassMiddleware
import minutes_db

from fasolaminutes_parsing.tokenizer import tokenize
from fasolaminutes_parsing.parse import parse

app = Flask(__name__)

# Hack fasolaminutes_parsing db location to the correct relative path
import fasolaminutes_parsing.minutes_db as parsing_db
parsing_db.dbname = minutes_db.dbname

# DB Stuff
def get_db():
    if not hasattr(g, 'db'):
        g.db = minutes_db.open()
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    if hasattr(g, 'db'):
        g.db.close()

# Routes
@app.route("/")
@app.route("/minutes")
def index():
    cursor = get_db().execute("SELECT id, name, location, date, year FROM minutes")
    return render_template('index.html', rows = cursor)

@app.route("/minutes/<int:minutes_id>")
def minutes(minutes_id):
    # Load and parse the minutes
    minutes = get_db().execute("""
        SELECT id, name, location, date, minutes
        FROM minutes
        WHERE id=?
    """, [minutes_id]).fetchone()
    split = request.args.get('split') is not None
    if request.args.get('raw') is not None:
        return render_template('minutes.html', minutes=minutes, split=split)
    leads, tokens = parse(minutes['minutes'], song_title=True, breaks=True)

    # Transform leads tokens into token ids
    for idx, lead in enumerate(leads):
        lead['leader_id'] = id(lead.pop('leader_token', None))
        lead['song_id'] = id(lead.pop('song_token', None))

    return render_template(
        'minutes.html',
        minutes=minutes,
        split=split,
        tokens=tokens,
        leads=leads
    )

if os.environ.get('FLASK_DEBUG'):
    # Sass debugging
    from sassutils.wsgi import SassMiddleware
    app.wsgi_app = SassMiddleware(app.wsgi_app, {
        __name__: ('static/sass', 'static/css', '/static/css')
    })
else:
    # Build all sass files once for production
    from sassutils.builder import build_directory
    build_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'sass'),
        os.path.join(os.path.dirname(__file__), 'static', 'css'),
    )

if __name__ == "__main__":
    from subprocess import call
    os.environ['FLASK_APP'] = __file__
    #os.environ['FLASK_DEBUG'] = '1'
    call(['flask', 'run'])
