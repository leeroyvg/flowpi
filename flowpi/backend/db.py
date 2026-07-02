import sqlite3
from pathlib import Path

from config.config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS flow (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        ml REAL,
        event TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_flow_user_id ON flow(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_flow_event_id ON flow(event, id DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_flow_timestamp ON flow(timestamp DESC)")

    conn.commit()
    conn.close()
