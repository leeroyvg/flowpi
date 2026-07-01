from backend.db import get_connection

def insert_flow(user_id, ml, event):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        INSERT INTO flow (user_id, ml, event)
        VALUES (?, ?, ?)
    """, (user_id, ml, event))

    conn.commit()
    conn.close()

def get_total_per_user():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT
            u.id,
            u.name,
            COALESCE(SUM(f.ml),0) as total
        FROM users u
        LEFT JOIN flow f ON u.id = f.user_id
        GROUP BY u.id, u.name
        ORDER BY u.id
    """)

    rows = c.fetchall()
    conn.close()

    return [
        {"id": r[0], "name": r[1], "ml": r[2]}
        for r in rows
    ]

def get_total():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT COALESCE(SUM(ml), 0)
        FROM flow
    """)

    total = c.fetchone()[0]

    conn.close()
    return total

def get_users():
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT id, name FROM users")
    rows = c.fetchall()

    conn.close()

    return [{"id": r[0], "name": r[1]} for r in rows]
