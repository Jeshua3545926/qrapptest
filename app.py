import sys
from pathlib import Path
from flask import Flask, request, session

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import SECRET_KEY
from services.auth_service import get_token_from_request, verify_jwt_token
from services.qr_service import generar_pdf_qrs

# Import blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.scanner import scanner_bp
from routes.api import api_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(scanner_bp)
app.register_blueprint(api_bp)

@app.before_request
def before_request():
    """Restore session from JWT token before each request"""
    if request.path.startswith('/static') or request.path == '/login':
        return
    
    token = get_token_from_request()
    if token:
        payload = verify_jwt_token(token)
        if payload:
            session['role'] = payload['role']
            session['user_id'] = payload['user_id']
            session['username'] = payload['username']

if __name__ == "__main__":
    try:
        generar_pdf_qrs()
    except Exception as e:
        print(f"Error al generar PDF de QRs: {str(e)}")
    app.run(host="0.0.0.0", port=5000, debug=True)
