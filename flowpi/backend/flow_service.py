import time
from threading import Lock

from config.config import ML_PER_PULSE, IDLE_TIMEOUT_SEC
from backend.repository import insert_flow

class FlowService:

    def __init__(self):
        self.current_user = 1
        self.tap_open = False
        self.pulse_count = 0
        self.last_count = 0
        self.last_pulse_time = 0
        self._lock = Lock()

    def register_pulse(self):
        with self._lock:
            self.pulse_count += 1
            self.last_pulse_time = time.time()

    def process(self):
        with self._lock:
            delta = self.pulse_count - self.last_count
            self.last_count = self.pulse_count
            last_pulse_time = self.last_pulse_time
            current_user = self.current_user
            tap_open = self.tap_open

        now = time.time()

        # TAP OPEN
        if delta > 0 and not tap_open:
            with self._lock:
                if not self.tap_open:
                    self.tap_open = True
                    tap_open = True
            insert_flow(current_user, 0, "TAP_OPEN")

        # FLOW
        if delta > 0:
            ml = delta * ML_PER_PULSE
            insert_flow(current_user, ml, "FLOW")

        # TAP CLOSE
        if tap_open and (now - last_pulse_time) > IDLE_TIMEOUT_SEC:
            with self._lock:
                if self.tap_open and (now - self.last_pulse_time) > IDLE_TIMEOUT_SEC:
                    self.tap_open = False
            insert_flow(current_user, 0, "TAP_CLOSE")

    def set_user(self, user_id):
        with self._lock:
            previous_user = self.current_user
            self.current_user = user_id
        insert_flow(previous_user, 0, "USER_SWITCH")

    def get_status(self):
        with self._lock:
            return {
                "tap_open": self.tap_open,
                "user": self.current_user,
            }
