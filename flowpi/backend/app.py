import atexit
import logging
from flask_cors import CORS
from flask import Flask, jsonify

import threading
import time

from config.config import ALLOWED_ORIGINS, DEBUG, ENABLE_GPIO, HOST, LOG_LEVEL, PORT
from backend.flow_service import FlowService
from backend.gpio import GPIOService
from backend.db import init_db
from backend.repository import get_total, get_total_per_user, get_users

LOGGER = logging.getLogger(__name__)

def configure_logging():
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

def loop(service, stop_event):
    while True:
        if stop_event.is_set():
            return
        time.sleep(1)
        service.process()

def create_app():
    configure_logging()
    init_db()

    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS or ["*"]}})

    service = FlowService()
    gpio = GPIOService(service)
    stop_event = threading.Event()

    app.config["FLOW_SERVICE"] = service
    app.config["GPIO_SERVICE"] = gpio
    app.config["STOP_EVENT"] = stop_event

    @app.get("/health")
    def health():
        return jsonify({
            "status": "ok",
            "gpio_enabled": gpio.enabled,
        })

    @app.get("/user_totals")
    def total():
        return jsonify(get_total_per_user())

    @app.get("/user_total")
    def totals():
        return jsonify({
            "total_ml": get_total()
        })

    @app.get("/users")
    def users():
        return jsonify(get_users())

    @app.post("/set_user/<int:user_id>")
    def set_user(user_id):
        valid_user_ids = {user["id"] for user in get_users()}
        if user_id not in valid_user_ids:
            return jsonify({"error": "Unknown user"}), 404

        service.set_user(user_id)
        return jsonify({
            "active_user": user_id
        })

    @app.get("/status")
    def status():
        return jsonify(service.get_status())

    if ENABLE_GPIO:
        gpio.setup()
    else:
        LOGGER.info("GPIO integration disabled by configuration")

    thread = threading.Thread(target=loop, args=(service, stop_event), daemon=True)
    thread.start()

    def shutdown_runtime():
        stop_event.set()
        gpio.cleanup()

    atexit.register(shutdown_runtime)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)
