import RPi.GPIO as GPIO
import time
import json
import threading
import statistics

PIN = 17

pulse_count = 0
lock = threading.Lock()


def pulse_callback(channel):
    global pulse_count
    with lock:
        pulse_count += 1


def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    GPIO.add_event_detect(
        PIN,
        GPIO.FALLING,
        callback=pulse_callback,
        bouncetime=5
    )


def reset_counter():
    global pulse_count
    with lock:
        pulse_count = 0


def get_pulses():
    with lock:
        return pulse_count


def save_config(avg_ml_per_pulse):
    config = {
        "flow_sensor": {
            "ml_per_pulse": avg_ml_per_pulse
        }
    }

    with open("flow_config.json", "w") as f:
        json.dump(config, f, indent=4)


def main():
    setup_gpio()

    print("=== MULTI RUN FLOW CALIBRATION ===")

    while True:
        try:
            runs = int(input("Hoeveel metingen wil je doen? (bijv. 3-5): "))
            if runs <= 0:
                print("Moet > 0 zijn")
                continue
            break
        except ValueError:
            print("Ongeldige invoer")

    results = []

    for i in range(runs):
        print(f"\n--- RUN {i + 1}/{runs} ---")
        input("Druk ENTER om START te beginnen...")

        reset_counter()
        print("Meten gestart...")

        input("Druk ENTER om STOP te zetten...")

        time.sleep(0.2)

        pulses = get_pulses()

        print(f"Pulses gemeten: {pulses}")

        if pulses == 0:
            print("⚠️ Geen pulses gemeten, run overgeslagen")
            continue

        while True:
            try:
                volume_l = float(input("Ingedragen volume (liter): "))
                if volume_l <= 0:
                    print("Moet > 0 zijn")
                    continue
                break
            except ValueError:
                print("Ongeldige invoer")

        ml = volume_l * 1000
        ml_per_pulse = ml / pulses

        print(f"ML/Pulse deze run: {ml_per_pulse:.6f}")

        results.append(ml_per_pulse)

    if len(results) == 0:
        print("Geen geldige metingen")
        GPIO.cleanup()
        return

    avg = statistics.mean(results)
    stdev = statistics.stdev(results) if len(results) > 1 else 0

    print("\n=== RESULTATEN ===")
    print(f"Runs: {len(results)}")
    print(f"Gemiddelde ML/Pulse: {avg:.6f}")
    print(f"Standaardafwijking: {stdev:.6f}")

    save_config(avg)

    print("\nConfiguratie opgeslagen in flow_config.json")

    GPIO.cleanup()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        GPIO.cleanup()