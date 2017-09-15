#!/usr/bin/env python
# encoding: utf-8

import os
import json
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
        # Update the Schema
        g.db.execute("""
            CREATE TABLE IF NOT EXISTS minutes_corrections (
                minutes_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                json TEXT,
                revision INT,
                PRIMARY KEY (minutes_id, user_id)
            )
        """)
    return g.db

def save_minutes_data(minutes_id, user, leads, revision=1):
    db = get_db()
    leads = json.dumps({'leads': leads})
    # Try to update first
    curs = db.execute("""
        UPDATE minutes_corrections
        SET json=?, revision=?
        WHERE minutes_id=? AND user_id=?
    """, [leads, revision, minutes_id, user])
    # Insert if that fails
    if curs.rowcount == 0:
        db.execute("""
            INSERT INTO minutes_corrections (minutes_id, user_id, json, revision)
            VALUES (?, ?, ?, ?)
        """, [minutes_id, user, leads, revision])
    db.commit()

def load_minutes_data(minutes_id, user):
    return get_db().execute("""
        SELECT * FROM minutes_corrections
        WHERE minutes_id=? AND user_id=?
    """, [minutes_id, user]).fetchone()

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

    # Load corrected minutes and join with the parsed minutes
    try:
        corrected = load_minutes_data(minutes_id, 'test-user')
        if corrected:
            leads = json.loads(corrected['json'])['leads']
    except ValueError:
        pass # Use the newly parsed leads

    return render_template(
        'minutes.html',
        minutes=minutes,
        split=split,
        tokens=tokens,
        leads=leads
    )

@app.route("/minutes-save/<int:minutes_id>", methods=['POST'])
def minutes_save(minutes_id):
    data = request.get_json()
    if not data or 'leads' not in data:
        return jsonify({'saved': False, 'reason': 'No leads'});
    if 'revision' not in data or 'user' not in data:
        return jsonify({'saved': False, 'reason': 'Missing data'});
    # We only care about song, leader, and original.song, original.leader, and
    # we want to throw away any other junk, like leader_id, song_id
    leads = []
    for lead in data['leads']:
        try:
            leads.append({
                'song': lead['song'],
                'leader': lead['leader'],
                'original': {
                    'song': lead['original']['song'],
                    'leader': lead['original']['leader']
                }
            })
        except KeyError:
            return jsonify({'saved': False, 'reason': 'song, leader, original.song, and original.leader must be present'});
    save_minutes_data(
        minutes_id=minutes_id,
        user=data['user'],
        revision=data['revision'],
        leads=leads,
    )
    return jsonify({'saved': True});

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
