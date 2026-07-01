import RPi.GPIO as GPIO
import time
import threading

PIN = 17
pulse_count = 0

ML_PER_PULSE = 2.25  # uit datasheet

last_time = time.time()
last_pulse_count = 0

active_user_id = 1  # tijdelijk hardcoded (later via UI)

lock = threading.Lock()


def pulse_callback(channel):
    global pulse_count
    with lock:
        pulse_count += 1


GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

GPIO.add_event_detect(
    PIN,
    GPIO.FALLING,
    callback=pulse_callback,
    bouncetime=5
)

print("Flow tracking started...")

try:
    while True:
        current_time = time.time()

        # atomic snapshot (belangrijk!)
        with lock:
            count = pulse_count
            prev_count = last_pulse_count

        ml_total = count * ML_PER_PULSE
        liters_total = ml_total / 1000

        pulses_diff = count - prev_count
        time_diff = current_time - last_time

        if time_diff > 0:
            ml_per_sec = (pulses_diff * ML_PER_PULSE) / time_diff
            l_min = (ml_per_sec * 60) / 1000
        else:
            l_min = 0

        print(
            f"Pulses: {count} | "
            f"Volume: {ml_total:.1f} ml ({liters_total:.3f} L) | "
            f"Flow: {l_min:.2f} L/min"
        )

        # update state AFTER calculation
        last_time = current_time
        last_pulse_count = count

        time.sleep(1)

except KeyboardInterrupt:
    GPIO.cleanup()