import time
from config.config import ML_PER_PULSE, IDLE_TIMEOUT_SEC
from backend.repository import insert_flow

class FlowService:

    def __init__(self):
        self.current_user = 1
        self.tap_open = False
        self.pulse_count = 0
        self.last_count = 0
        self.last_pulse_time = 0

    def register_pulse(self):
        self.pulse_count += 1
        self.last_pulse_time = time.time()

    def process(self):
        delta = self.pulse_count - self.last_count
        self.last_count = self.pulse_count

        now = time.time()

        # TAP OPEN
        if delta > 0 and not self.tap_open:
            self.tap_open = True
            insert_flow(self.current_user, 0, "TAP_OPEN")

        # FLOW
        if delta > 0:
            ml = delta * ML_PER_PULSE
            insert_flow(self.current_user, ml, "FLOW")

        # TAP CLOSE
        if self.tap_open and (now - self.last_pulse_time) > IDLE_TIMEOUT_SEC:
            self.tap_open = False
            insert_flow(self.current_user, 0, "TAP_CLOSE")

    def set_user(self, user_id):
        insert_flow(self.current_user, 0, "USER_SWITCH")
        self.current_user = user_id
