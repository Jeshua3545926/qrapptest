import os
from pathlib import Path

# Flask configuration
SECRET_KEY = os.getenv("SECRET_KEY", "cambia_esta_clave_secreta")
JWT_SECRET = os.getenv("JWT_SECRET", "qr_asistencia_secret_key_2024_fixed")

# Environment: local or production
ENVIRONMENT = os.getenv("ENVIRONMENT", "prduction")

# Paths
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"
QR_DIR = BASE_DIR / "static" / "qrcodes"
PDF_DIR = BASE_DIR / "static" / "pdfs"

# SMTP/Email configuration
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = os.getenv("SMTP_PORT", "465")
SMTP_SECURITY = os.getenv("SMTP_SECURITY", "ssl")

# Base URL configuration
if ENVIRONMENT == "production":
    BASE_URL = os.getenv("BASE_URL", "https://appqr-g3ft.onrender.com")
else:
    # For local, don't use BASE_URL from env var to avoid conflicts
    BASE_URL = "http://127.0.0.1:5000"
