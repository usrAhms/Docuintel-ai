"""Local SQLite reviewer decisions; never uploads documents to a remote service."""
import sqlite3
from pathlib import Path

SCHEMA = '''CREATE TABLE IF NOT EXISTS reviews (
    sha256 TEXT PRIMARY KEY, status TEXT NOT NULL, reviewer TEXT NOT NULL,
    notes TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)'''


def connection(path: str | Path):
    db = sqlite3.connect(str(path))
    db.execute(SCHEMA)
    db.commit()
    return db


def get_review(db, sha256):
    row = db.execute('SELECT status,reviewer,notes,updated_at FROM reviews WHERE sha256=?',(sha256,)).fetchone()
    return {'status':row[0],'reviewer':row[1],'notes':row[2],'updated_at':row[3]} if row else None


def save_review(db,sha256,status,reviewer,notes):
    if status not in {'Unreviewed','Needs follow-up','Cleared'}:
        raise ValueError('Invalid review status')
    db.execute('''INSERT INTO reviews (sha256,status,reviewer,notes) VALUES (?,?,?,?)
    ON CONFLICT(sha256) DO UPDATE SET status=excluded.status,reviewer=excluded.reviewer,
    notes=excluded.notes,updated_at=CURRENT_TIMESTAMP''',(sha256,status,reviewer[:80],notes[:2000]))
    db.commit()
