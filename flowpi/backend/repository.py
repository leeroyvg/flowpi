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


def get_user_total(user_id):
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        SELECT COALESCE(SUM(ml), 0)
        FROM flow
        WHERE user_id = ?
    """,
        (user_id,),
    )

    total = c.fetchone()[0]
    conn.close()
    return total


def adjust_user_total(user_id, delta_ml):
    if float(delta_ml) == 0.0:
        return

    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        INSERT INTO flow (user_id, ml, event)
        VALUES (?, ?, ?)
    """,
        (user_id, float(delta_ml), "ADMIN_ADJUST"),
    )

    conn.commit()
    conn.close()


def set_user_name(user_id, name):
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        UPDATE users
        SET name = ?
        WHERE id = ?
    """,
        (str(name), user_id),
    )

    conn.commit()
    conn.close()


def create_user(name):
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        INSERT INTO users (name)
        VALUES (?)
    """,
        (str(name),),
    )

    user_id = c.lastrowid
    conn.commit()
    conn.close()
    return user_id


def delete_user(user_id):
    conn = get_connection()
    c = conn.cursor()

    c.execute("DELETE FROM flow WHERE user_id = ?", (user_id,))
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))

    conn.commit()
    conn.close()

def get_users():
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT id, name FROM users")
    rows = c.fetchall()

    conn.close()

    return [{"id": r[0], "name": r[1]} for r in rows]
