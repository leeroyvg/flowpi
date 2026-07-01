# flowpi

FlowPi is a Raspberry Pi flow-meter dashboard with a Flask API, SQLite storage, and a lightweight browser UI.

## Production-ready changes

- Backend startup now uses an app factory with environment-based configuration.
- GPIO access degrades cleanly when `RPi.GPIO` is unavailable, which keeps local development and CI usable.
- Database initialization creates the data directory automatically.
- The API now exposes a `/health` endpoint and validates user switches.
- Frontend API access no longer depends on a hard-coded IP address.
- Runtime dependencies are declared in [flowpi/requirements.txt](flowpi/requirements.txt).

## Backend configuration

The backend reads these environment variables:

- `FLOWPI_DB_PATH`: SQLite database file path. Defaults to `flowpi/data/flow.db`.
- `FLOWPI_DATA_DIR`: base data directory when `FLOWPI_DB_PATH` is not set.
- `FLOWPI_ENABLE_GPIO`: `true` or `false`. Disable for local development and testing.
- `FLOWPI_ALLOWED_ORIGINS`: comma-separated CORS allowlist. Use an explicit allowlist in production instead of `*`.
- `FLOWPI_HOST`: bind host. Defaults to `0.0.0.0`.
- `FLOWPI_PORT`: API port. Defaults to `5000`.
- `FLOWPI_LOG_LEVEL`: logging level such as `INFO` or `DEBUG`.
- `FLOWPI_ML_PER_PULSE`: flow calibration factor.
- `FLOWPI_IDLE_TIMEOUT_SEC`: tap idle timeout in seconds.

## Local setup

```bash
cd flowpi
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export FLOWPI_ENABLE_GPIO=false
python -m backend.app
```

Open the frontend by serving [flowpi/frontend/index.html](flowpi/frontend/index.html) from any static server on the same host, or configure `window.FLOWPI_API_BASE` before loading [flowpi/frontend/app.js](flowpi/frontend/app.js).

## Production start

On the Raspberry Pi, install the Python dependencies and run:

```bash
cd flowpi
pip install -r requirements.txt
FLOWPI_ALLOWED_ORIGINS=http://<pi-ip>:8000 ./run.sh
```

The launcher uses `waitress-serve` for the backend and `python3 -m http.server` for the frontend.

## Validation

Run the backend smoke tests with:

```bash
cd flowpi
python -m unittest tests.test_app
```