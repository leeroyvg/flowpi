import RPi.GPIO as GPIO
import time
import threading
import sqlite3
from flask import Flask, jsonify

app = Flask(__name__)

PIN = 17
ML_PER_PULSE = 2.25
IDLE_TIMEOUT = 5

pulse_count = 0
last_count = 0
last_pulse_time = 0

tap_open = False
current_user = 1
lock = threading.Lock()

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect("flow.db")
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
    c.execute("""
        CREATE TABLE IF NOT EXISTS flow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            ml REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # default users
    c.execute("INSERT OR IGNORE INTO users (id, name) VALUES (1, 'User 1')")
    c.execute("INSERT OR IGNORE INTO users (id, name) VALUES (2, 'User 2')")

    conn.commit()
    conn.close()

def insert_flow(user_id, ml):
    conn = sqlite3.connect("flow.db")
    c = conn.cursor()

    c.execute("INSERT INTO flow (user_id, ml) VALUES (?, ?)", (user_id, ml))

    conn.commit()
    conn.close()

# ---------------- GPIO ----------------
def pulse_callback(channel):
    global pulse_count, last_pulse_time
    with lock:
        pulse_count += 1
        last_pulse_time = time.time()

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(PIN, GPIO.FALLING, callback=pulse_callback, bouncetime=5)

# ---------------- FLOW LOOP ----------------
def flow_loop():
    global last_count, tap_open

    while True:
        time.sleep(1)

        now = time.time()

        with lock:
            delta = pulse_count - last_count
            last_count = pulse_count
            user = current_user

        if delta > 0:
            if not tap_open:
                tap_open = True

            ml = delta * ML_PER_PULSE
            insert_flow(user, ml)

        if tap_open and (now - last_pulse_time) > IDLE_TIMEOUT:
            tap_open = False

# ---------------- API ----------------
@app.route("/")
def home():
    return "Flow backend is running"

@app.route("/users")
def users():
    conn = sqlite3.connect("flow.db")
    c = conn.cursor()

    c.execute("SELECT id, name FROM users")
    data = [{"id": r[0], "name": r[1]} for r in c.fetchall()]

    conn.close()
    return jsonify(data)

@app.route("/totals")
def totals():
    conn = sqlite3.connect("flow.db")
    c = conn.cursor()

    c.execute("""
        SELECT users.id, users.name, COALESCE(SUM(flow.ml),0)
        FROM users
        LEFT JOIN flow ON users.id = flow.user_id
        GROUP BY users.id
    """)

    data = [{"id": r[0], "name": r[1], "ml": r[2]} for r in c.fetchall()]

    conn.close()
    return jsonify(data)

@app.route("/set_user/<int:user_id>")
def set_user(user_id):
    global current_user
    current_user = user_id
    return jsonify({"active_user": current_user})

@app.route("/status")
def status():
    with lock:
        return jsonify({
            "active_user": current_user,
            "tap_open": tap_open
        })

# ---------------- START ----------------
if __name__ == "__main__":
    init_db()

    t = threading.Thread(target=flow_loop, daemon=True)
    t.start()

    app.run(host="0.0.0.0", port=5000)
