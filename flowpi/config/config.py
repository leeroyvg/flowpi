import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("FLOWPI_DATA_DIR", BASE_DIR / "data"))

# GPIO
FLOW_PIN = int(os.getenv("FLOWPI_FLOW_PIN", "17"))

# Flow sensor calibration
ML_PER_PULSE = float(os.getenv("FLOWPI_ML_PER_PULSE", "2.25"))

# Timing
IDLE_TIMEOUT_SEC = int(os.getenv("FLOWPI_IDLE_TIMEOUT_SEC", "5"))

# Database
DB_PATH = str(Path(os.getenv("FLOWPI_DB_PATH", DATA_DIR / "flow.db")))

# HTTP
HOST = os.getenv("FLOWPI_HOST", "0.0.0.0")
PORT = int(os.getenv("FLOWPI_PORT", "5000"))
DEBUG = os.getenv("FLOWPI_DEBUG", "false").lower() in {"1", "true", "yes", "on"}

# CORS
ALLOWED_ORIGINS = [
	origin.strip()
	for origin in os.getenv("FLOWPI_ALLOWED_ORIGINS", "*").split(",")
	if origin.strip()
]

# Runtime
ENABLE_GPIO = os.getenv("FLOWPI_ENABLE_GPIO", "true").lower() in {"1", "true", "yes", "on"}
LOG_LEVEL = os.getenv("FLOWPI_LOG_LEVEL", "INFO").upper()
