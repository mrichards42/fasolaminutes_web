#!/usr/bin/env python
# encoding: utf-8

import os
import re
import sqlite3
from flask import Flask, g, request, render_template, jsonify
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

@app.route("/minutes/<int:id>")
def minutes(id):
    minutes = get_db().execute("""
        SELECT id, name, location, date, minutes
        FROM minutes
        WHERE id=?
    """, [id]).fetchone()
    split = request.args.get('split') is not None
    if request.args.get('raw') is not None:
        return render_template('minutes.html', minutes=minutes, split=split)

    return render_template(
        'minutes.html',
        minutes=minutes,
        split=split,
        tokens=tokenize(minutes['minutes']),
        leads=parse(minutes['minutes'], song_title=True, breaks=True)
    )

@app.route("/search/<table>/<fields>")
def search(table, fields=''):
    """Query a db table, returning json.

    Query params:
        q -- the search term
        fields -- additional columns to return

    """
    fields = fields.split(',')
    term = request.args.get('q')
    select_fields = request.args.get('fields', [])
    if select_fields:
        select_fields = set(['id'] + fields + select_fields.split(','))

    # Guard against bad table/field combos
    for name in [table] + fields + list(select_fields):
         if not re.match(r'^\w+$', name):
            if os.environ.get('FLASK_DEBUG'):
                raise Exception("Bad name: %r" % name)
            return jsonify(results=[])

    if not term:
        return jsonify(results=[])

    # Build a query:
    # SELECT id, <fields> FROM <table>
    sql = "SELECT " + ','.join(select_fields or ['*']) + " FROM " + table

    # WHERE <field> LIKE %searchterm% OR <field> LIKE %searchterm% ...
    sql += " WHERE "
    sql += " OR ".join(f + " LIKE ?" for f in fields)
    args = ['%' + term + '%'] * len(fields)

    sql += " LIMIT 20"
    results = []
    try:
        for row in get_db().execute(sql, args):
            results.append(dict(zip(row.keys(), row)))
        return jsonify(results=results);
    except sqlite3.Error as e:
        if os.environ.get('FLASK_DEBUG'):
            raise
        return jsonify(results=[])

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
    os.environ['FLASK_DEBUG'] = '1'
    call(['flask', 'run'])
