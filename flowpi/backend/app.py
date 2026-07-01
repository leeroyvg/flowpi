from flask import Flask, jsonify
from flask_cors import CORS

import threading
import time

from backend.flow_service import FlowService
from backend.gpio import GPIOService
from backend.db import init_db
from backend.repository import get_total, get_total_per_user, get_users

app = Flask(__name__)
CORS(app, resources={
    r"/*": {"origins": "*"}
})

service = FlowService()
gpio = GPIOService(service)

# ---------------- LOOP ----------------
def loop():
    while True:
        time.sleep(1)
        service.process()

# ---------------- API ----------------

@app.route("/user_totals")
def total():
    return jsonify(get_total_per_user())

@app.route("/user_total")
def totals():
    return jsonify({
        "total_ml": get_total()
    })

@app.route("/users")
def users():
    return jsonify(get_users())

@app.route("/set_user/<int:user_id>")
def set_user(user_id):
    service.set_user(user_id)
    return jsonify({
        "active_user": user_id
    })

@app.route("/status")
def status():
    return jsonify({
        "tap_open": service.tap_open,
        "user": service.current_user
    })

# ---------------- START ----------------
if __name__ == "__main__":
    init_db()
    gpio.setup()

    t = threading.Thread(target=loop, daemon=True)
    t.start()

    app.run(host="0.0.0.0", port=5000)
