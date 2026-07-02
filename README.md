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
- `FLOWPI_ENV`: runtime environment marker (`development` or `production`).
- `FLOWPI_ENABLE_GPIO`: `true` or `false`. Disable for local development and testing.
- `FLOWPI_ALLOWED_ORIGINS`: comma-separated CORS allowlist.
- `FLOWPI_HOST`: bind host. Defaults to `0.0.0.0`.
- `FLOWPI_PORT`: API port. Defaults to `5000`.
- `FLOWPI_LOG_LEVEL`: logging level such as `INFO` or `DEBUG`.
- `FLOWPI_TRUST_PROXY`: trust `X-Forwarded-*` headers from a reverse proxy.
- `FLOWPI_MAX_REQUEST_BYTES`: max request payload size in bytes.
- `FLOWPI_ML_PER_PULSE`: flow calibration factor.
- `FLOWPI_IDLE_TIMEOUT_SEC`: tap idle timeout in seconds.
- `FLOWPI_ADMIN_TOKEN`: optional static fallback token for admin API calls.
- `FLOWPI_ADMIN_USERNAME`: admin username for the login page.
- `FLOWPI_ADMIN_PASSWORD`: admin password for the login page.
- `FLOWPI_ADMIN_SESSION_TTL_SEC`: session duration in seconds. Defaults to `43200`.

## Local setup

### macOS/Linux

```bash
cd flowpi
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export FLOWPI_ENABLE_GPIO=false
python -m backend.app
```

### Windows (PowerShell)

```powershell
cd flowpi
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:FLOWPI_ENABLE_GPIO = "false"
$env:FLOWPI_ADMIN_USERNAME = "admin"
$env:FLOWPI_ADMIN_PASSWORD = "change-me"
python -m backend.app
```

Start backend and frontend together with the Windows launcher:

```powershell
cd flowpi
.\run.ps1
```

Recommended: use `run.ps1` as the default startup command on Windows, because it sets the correct project Python path and avoids `ModuleNotFoundError`/stale backend process issues.

If PowerShell blocks activation scripts, allow them for your user once:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Open the frontend by serving [flowpi/frontend/index.html](flowpi/frontend/index.html) from any static server on the same host, or configure `window.FLOWPI_API_BASE` before loading [flowpi/frontend/app.js](flowpi/frontend/app.js).

Admin management page: [flowpi/frontend/admin.html](flowpi/frontend/admin.html)
Statistics page: [flowpi/frontend/stats.html](flowpi/frontend/stats.html)

To edit volumes as admin in the UI:

1. Set `FLOWPI_ADMIN_USERNAME` and `FLOWPI_ADMIN_PASSWORD` on the backend.
2. Open `admin.html` from the frontend server.
3. Sign in with username and password.
4. Add new users with the `Add User` form.
5. Update user names and totals in liters, then click `Save`.
6. Remove users with `Delete`.

## Production start

On the Raspberry Pi, install the Python dependencies and run:

```bash
cd flowpi
pip install -r requirements.txt
FLOWPI_ALLOWED_ORIGINS=http://<pi-ip>:8000 ./run.sh
```

The launcher uses `waitress-serve` for the backend and `python3 -m http.server` for the frontend.

## Production hardening checklist

- Use strong secrets for `FLOWPI_ADMIN_PASSWORD` and optionally `FLOWPI_ADMIN_TOKEN`.
- Restrict `FLOWPI_ALLOWED_ORIGINS` to your frontend host(s), never `*` in production.
- Keep `FLOWPI_DEBUG=false` in production.
- If deployed behind Nginx/Caddy/Traefik, set `FLOWPI_TRUST_PROXY=true`.
- Persist `flowpi/data` on durable storage and include it in your backups.
- Monitor `/health` for liveness and `/ready` for readiness.

## Docker deployment

The project now includes a production container setup:

1. Copy `.env.example` to `.env` inside `flowpi/`.
2. Update credentials and origin allowlist in `.env`.
3. Start with Docker Compose:

```bash
cd flowpi
docker compose up -d --build
```

This starts:

- backend on `http://localhost:5000`
- frontend on `http://localhost:8000`

Data is persisted via the `./data:/app/data` volume mapping.

## Validation

Run the backend smoke tests with:

```bash
cd flowpi
python -m unittest tests.test_app
```