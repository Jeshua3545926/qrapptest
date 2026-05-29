from datetime import datetime, timedelta
from pathlib import Path
import os

app.secret_key = os.getenv("SECRET_KEY", "cambia_esta_clave_secreta")
JWT_SECRET = os.getenv("JWT_SECRET", "jwt_secret_key_cambiar_en_produccion")
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"
QR_DIR = BASE_DIR / "static" / "qrcodes"
PDF_DIR = BASE_DIR / "static" / "pdfs"

SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = os.getenv("SMTP_PORT", "465")
SMTP_SECURITY = os.getenv("SMTP_SECURITY", "ssl")
BASE_URL = os.getenv("BASE_URL", "https://appqr-g3ft.onrender.com")