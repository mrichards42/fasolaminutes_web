import sqlite3
import re

dbname = 'fasolaminutes_parsing/minutes.db'

newline_re = re.compile(r"\s*\\n+\s*")
def parse_text(text):
    """Parse as either UTF-8 or Mac Roman"""
    try:
        text = text.decode('utf-8')
    except UnicodeDecodeError:
        text = text.decode('mac-roman')

    # Some text contains literal newlines (that should just be spaces)
    if '\\n' in text:
        text = newline_re.sub(' ', text)
    # Minutes text is separated on vertical newlines
    text = text.replace('\v', '\n')
    return text

sqlite3.register_converter("TEXT", parse_text)

def open():
    """Open and return the minutes db"""
    db = sqlite3.connect(dbname, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    return db
