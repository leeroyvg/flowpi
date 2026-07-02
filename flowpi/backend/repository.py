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


def get_tap_stats():
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN event = 'FLOW' THEN ml ELSE 0 END), 0) AS total_flow_ml,
            COALESCE(SUM(CASE WHEN event = 'TAP_OPEN' THEN 1 ELSE 0 END), 0) AS tap_count
        FROM flow
    """
    )

    row = c.fetchone()
    conn.close()

    total_flow_ml = float(row[0] or 0)
    tap_count = int(row[1] or 0)
    average_ml = (total_flow_ml / tap_count) if tap_count > 0 else 0.0

    return {
        "total_flow_ml": total_flow_ml,
        "tap_count": tap_count,
        "avg_ml_per_tap": average_ml,
    }


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


def get_flow_events(limit=100):
    safe_limit = max(1, min(int(limit), 500))

    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        SELECT f.id, f.user_id, u.name, f.ml, f.event, f.timestamp
        FROM flow f
        LEFT JOIN users u ON u.id = f.user_id
        ORDER BY f.id DESC
        LIMIT ?
    """,
        (safe_limit,),
    )

    rows = c.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "user_id": r[1],
            "user_name": r[2] or "Unknown user",
            "ml": float(r[3] or 0),
            "event": r[4],
            "timestamp": r[5],
        }
        for r in rows
    ]


def get_recent_tap_sessions(limit=8):
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        SELECT f.id, f.user_id, f.ml, f.event, f.timestamp, u.name
        FROM flow f
        LEFT JOIN users u ON u.id = f.user_id
        WHERE f.event IN ('TAP_OPEN', 'FLOW', 'TAP_CLOSE')
        ORDER BY f.id ASC
    """
    )

    rows = c.fetchall()
    conn.close()

    sessions = []
    current = None

    for _, user_id, ml, event, timestamp, user_name in rows:
        if event == "TAP_OPEN":
            current = {
                "user_id": user_id,
                "user_name": user_name or "Unknown user",
                "total_ml": 0.0,
                "opened_at": timestamp,
                "closed_at": None,
                "state": "open",
            }
            continue

        if not current:
            continue

        if event == "FLOW":
            current["total_ml"] += float(ml or 0)
            continue

        if event == "TAP_CLOSE":
            current["closed_at"] = timestamp
            current["state"] = "closed"
            sessions.append(current)
            current = None

    if current:
        sessions.append(current)

    return list(reversed(sessions[-max(int(limit), 1):]))
