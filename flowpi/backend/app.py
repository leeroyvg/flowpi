import atexit
import hmac
import logging
import secrets
from flask_cors import CORS
from flask import Flask, jsonify, request

import threading
import time

from config.config import (
    ADMIN_PASSWORD,
    ADMIN_SESSION_TTL_SEC,
    ADMIN_TOKEN,
    ADMIN_USERNAME,
    ALLOWED_ORIGINS,
    DEBUG,
    ENABLE_GPIO,
    HOST,
    LOG_LEVEL,
    PORT,
)
from backend.flow_service import FlowService
from backend.gpio import GPIOService
from backend.db import init_db
from backend.repository import (
    adjust_user_total,
    create_user,
    delete_user,
    get_recent_tap_sessions,
    get_tap_stats,
    get_total,
    get_total_per_user,
    get_user_total,
    get_users,
    set_user_name,
)

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
    admin_sessions = {}
    admin_lock = threading.Lock()

    app.config["FLOW_SERVICE"] = service
    app.config["GPIO_SERVICE"] = gpio
    app.config["STOP_EVENT"] = stop_event

    def find_user_name(user_id):
        if user_id is None:
            return None

        for user in get_users():
            if user["id"] == user_id:
                return user["name"]

        return None

    def cleanup_admin_sessions(now=None):
        now = now or time.time()
        with admin_lock:
            expired_tokens = [token for token, expires_at in admin_sessions.items() if expires_at <= now]
            for token in expired_tokens:
                admin_sessions.pop(token, None)

    def issue_admin_session():
        cleanup_admin_sessions()
        token = secrets.token_urlsafe(32)
        expires_at = time.time() + max(ADMIN_SESSION_TTL_SEC, 60)
        with admin_lock:
            admin_sessions[token] = expires_at
        return token, expires_at

    def has_valid_admin_session(session_token):
        if not session_token:
            return False

        cleanup_admin_sessions()
        with admin_lock:
            expires_at = admin_sessions.get(session_token)
            if not expires_at:
                return False
            return expires_at > time.time()

    def is_admin_authorized():
        session_token = request.headers.get("X-Admin-Session", "")
        if has_valid_admin_session(session_token):
            return True

        request_token = request.headers.get("X-Admin-Token", "")
        return bool(ADMIN_TOKEN) and hmac.compare_digest(request_token, ADMIN_TOKEN)

    @app.get("/health")
    def health():
        return jsonify({
            "status": "ok",
            "gpio_enabled": gpio.enabled,
            "admin_login_enabled": bool(ADMIN_USERNAME and ADMIN_PASSWORD),
        })

    @app.post("/admin/login")
    def admin_login():
        if not ADMIN_USERNAME or not ADMIN_PASSWORD:
            return jsonify({"error": "Admin login is not configured"}), 503

        payload = request.get_json(silent=True) or {}
        username = str(payload.get("username", ""))
        password = str(payload.get("password", ""))

        valid_username = hmac.compare_digest(username, ADMIN_USERNAME)
        valid_password = hmac.compare_digest(password, ADMIN_PASSWORD)

        if not (valid_username and valid_password):
            return jsonify({"error": "Invalid credentials"}), 401

        session_token, expires_at = issue_admin_session()
        return jsonify(
            {
                "session_token": session_token,
                "expires_at": int(expires_at),
                "expires_in_sec": int(max(0, expires_at - time.time())),
            }
        )

    @app.get("/admin/session")
    def admin_session():
        session_token = request.headers.get("X-Admin-Session", "")
        return jsonify({"authenticated": has_valid_admin_session(session_token)})

    @app.post("/admin/logout")
    def admin_logout():
        session_token = request.headers.get("X-Admin-Session", "")
        if session_token:
            with admin_lock:
                admin_sessions.pop(session_token, None)
        return jsonify({"ok": True})

    @app.get("/user_totals")
    def total():
        return jsonify(get_total_per_user())

    @app.get("/user_total")
    def totals():
        return jsonify({
            "total_ml": get_total()
        })

    @app.get("/tap_stats")
    def tap_stats():
        return jsonify(get_tap_stats())

    @app.get("/tap_sessions")
    def tap_sessions():
        return jsonify(get_recent_tap_sessions(limit=8))

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
            "active_user": user_id,
            "active_user_name": find_user_name(user_id),
        })

    @app.post("/admin/users/<int:user_id>/volume")
    def admin_set_user_volume(user_id):
        if not is_admin_authorized():
            return jsonify({"error": "Forbidden"}), 403

        valid_user_ids = {user["id"] for user in get_users()}
        if user_id not in valid_user_ids:
            return jsonify({"error": "Unknown user"}), 404

        payload = request.get_json(silent=True) or {}
        if "total_ml" not in payload:
            return jsonify({"error": "total_ml is required"}), 400

        try:
            target_total_ml = float(payload["total_ml"])
        except (TypeError, ValueError):
            return jsonify({"error": "total_ml must be a number"}), 400

        if target_total_ml < 0:
            return jsonify({"error": "total_ml must be >= 0"}), 400

        current_total_ml = float(get_user_total(user_id))
        delta_ml = target_total_ml - current_total_ml

        adjust_user_total(user_id, delta_ml)

        return jsonify({
            "user_id": user_id,
            "user_name": find_user_name(user_id),
            "previous_total_ml": current_total_ml,
            "total_ml": target_total_ml,
            "delta_ml": delta_ml,
        })

    @app.post("/admin/users/<int:user_id>/name")
    def admin_set_user_name(user_id):
        if not is_admin_authorized():
            return jsonify({"error": "Forbidden"}), 403

        valid_user_ids = {user["id"] for user in get_users()}
        if user_id not in valid_user_ids:
            return jsonify({"error": "Unknown user"}), 404

        payload = request.get_json(silent=True) or {}
        name = str(payload.get("name", "")).strip()

        if not name:
            return jsonify({"error": "name is required"}), 400

        if len(name) > 40:
            return jsonify({"error": "name is too long (max 40)"}), 400

        set_user_name(user_id, name)

        return jsonify({
            "user_id": user_id,
            "user_name": name,
            "name": name,
        })

    @app.post("/admin/users")
    def admin_create_user():
        if not is_admin_authorized():
            return jsonify({"error": "Forbidden"}), 403

        payload = request.get_json(silent=True) or {}
        name = str(payload.get("name", "")).strip()

        if not name:
            return jsonify({"error": "name is required"}), 400

        if len(name) > 40:
            return jsonify({"error": "name is too long (max 40)"}), 400

        user_id = create_user(name)
        return jsonify({"id": user_id, "name": name, "user_name": name}), 201

    @app.delete("/admin/users/<int:user_id>")
    def admin_delete_user(user_id):
        if not is_admin_authorized():
            return jsonify({"error": "Forbidden"}), 403

        users = get_users()
        deleted_user_name = next((user["name"] for user in users if user["id"] == user_id), None)
        valid_user_ids = [user["id"] for user in users]
        if user_id not in valid_user_ids:
            return jsonify({"error": "Unknown user"}), 404

        if len(valid_user_ids) <= 1:
            return jsonify({"error": "At least one user must remain"}), 400

        service = app.config["FLOW_SERVICE"]
        switched_to = None
        if service.current_user == user_id:
            switched_to = next(uid for uid in valid_user_ids if uid != user_id)
            service.set_user(switched_to)

        delete_user(user_id)

        return jsonify({
            "deleted_user_id": user_id,
            "deleted_user_name": deleted_user_name,
            "switched_to": switched_to,
            "switched_to_name": find_user_name(switched_to),
        })

    @app.get("/status")
    def status():
        current = service.get_status()
        return jsonify({
            **current,
            "user_name": find_user_name(current.get("user")),
        })

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
