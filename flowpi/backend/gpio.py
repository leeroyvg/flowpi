import RPi.GPIO as GPIO
from config.config import FLOW_PIN

class GPIOService:

    def __init__(self, service):
        self.service = service

    def setup(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(FLOW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(
            FLOW_PIN,
            GPIO.FALLING,
            callback=self._pulse,
            bouncetime=5
        )

    def _pulse(self, channel):
        self.service.register_pulse()
