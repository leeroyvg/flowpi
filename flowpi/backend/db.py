import sqlite3
from config.config import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS flow (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        ml REAL,
        event TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # default users
    for i in range(1, 11):
        c.execute(
            "INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)",
            (i, f"User {i}")
        )

    conn.commit()
    conn.close()
