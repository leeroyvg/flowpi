import logging

from config.config import FLOW_PIN

try:
    import RPi.GPIO as GPIO
except ImportError:  # pragma: no cover - depends on Raspberry Pi runtime
    GPIO = None


LOGGER = logging.getLogger(__name__)

class GPIOService:

    def __init__(self, service):
        self.service = service
        self.enabled = GPIO is not None

    def setup(self):
        if GPIO is None:
            LOGGER.warning("RPi.GPIO is unavailable; running without hardware pulse capture")
            return False

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(FLOW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(
            FLOW_PIN,
            GPIO.FALLING,
            callback=self._pulse,
            bouncetime=5
        )
        self.enabled = True
        return True

    def _pulse(self, channel):
        self.service.register_pulse()

    def cleanup(self):
        if GPIO is not None and self.enabled:
            GPIO.cleanup(FLOW_PIN)
