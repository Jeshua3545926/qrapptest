from flask import Flask, render_template, request, redirect, jsonify, send_file, session, url_for
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import pandas as pd
import qrcode
import hashlib
import jwt
from functools import wraps
import pytz
import io

app = Flask(__name__)

# Zona horaria de México (UTC-6)
mexico_tz = pytz.timezone('America/Mexico_City')
def get_mexico_time():
    """Obtener la fecha y hora actual en zona horaria de México"""
    return datetime.now(mexico_tz).strftime("%Y-%m-%d %H:%M:%S")

def get_mexico_datetime():
    """Obtener el datetime actual en zona horaria de México"""
    return datetime.now(mexico_tz)

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

def save_excel():
    """Guarda el registro en formato excel"""
    conn = get_db()
    registros = conn.execute('''
        SELECT registros.id, empleados.nombre AS empleado, locales.nombre AS local, registros.fecha
        FROM registros
        JOIN empleados ON registros.empleado_id = empleados.id
        JOIN locales ON registros.local_id = locales.id
        ORDER BY registros.fecha DESC
    ''').fetchall()
    conn.close()

    # Crear DataFrame
    df = pd.DataFrame(registros, columns=['ID', 'Empleado', 'Local', 'Fecha'])
    
    # Crear archivo Excel en memoria
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Registros')
    output.seek(0)
    
    return output



def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def generate_jwt_token(role, user_id, username):
    payload = {
        'role': role,
        'user_id': user_id,
        'username': username,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        print(f"DEBUG: Token verified successfully. Payload: {payload}")
        return payload
    except jwt.ExpiredSignatureError:
        print("DEBUG: Token expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"DEBUG: Invalid token: {e}")
        return None

def get_token_from_request():
    # Try to get token from Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        print(f"DEBUG: Token from Authorization header: {auth_header[:20]}...")
        return auth_header.split(' ')[1]
    
    # Try to get token from query parameter
    token = request.args.get('token')
    if token:
        print(f"DEBUG: Token from query parameter: {token[:20]}...")
        return token
    
    # Try to get token from cookie
    token = request.cookies.get('jwt_token')
    if token:
        print(f"DEBUG: Token from cookie: {token[:20]}...")
        return token
    
    print("DEBUG: No token found in request")
    return None

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_admin_schema():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(admins)")
    columns = [row[1] for row in cur.fetchall()]
    schema_updates = [
        ("email", "ALTER TABLE admins ADD COLUMN email TEXT"),
        ("smtp_host", "ALTER TABLE admins ADD COLUMN smtp_host TEXT"),
        ("smtp_port", "ALTER TABLE admins ADD COLUMN smtp_port INTEGER"),
        ("smtp_security", "ALTER TABLE admins ADD COLUMN smtp_security TEXT"),
        ("smtp_email", "ALTER TABLE admins ADD COLUMN smtp_email TEXT"),
        ("smtp_password", "ALTER TABLE admins ADD COLUMN smtp_password TEXT"),
        ("admin_email_destino", "ALTER TABLE admins ADD COLUMN admin_email_destino TEXT"),
        ("sendgrid_api_key", "ALTER TABLE admins ADD COLUMN sendgrid_api_key TEXT"),
    ]
    for column_name, sql in schema_updates:
        if column_name not in columns:
            cur.execute(sql)
            conn.commit()
    conn.close()

def ensure_qrs_generados_schema():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qrs_generados'")
    table_exists = cur.fetchone()
    if not table_exists:
        cur.execute("""
            CREATE TABLE qrs_generados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_local TEXT NOT NULL,
                nombre_empleado TEXT NOT NULL,
                fecha TEXT NOT NULL,
                hora TEXT NOT NULL,
                token TEXT NOT NULL,
                admin_id INTEGER,
                creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
                visible INTEGER DEFAULT 1,
                qr_imagen TEXT
            )
        """)
        conn.commit()
    else:
        # Check if visible column exists, add it if not
        cur.execute("PRAGMA table_info(qrs_generados)")
        columns = [row[1] for row in cur.fetchall()]
        if "visible" not in columns:
            cur.execute("ALTER TABLE qrs_generados ADD COLUMN visible INTEGER DEFAULT 1")
            conn.commit()
        if "qr_imagen" not in columns:
            cur.execute("ALTER TABLE qrs_generados ADD COLUMN qr_imagen TEXT")
            conn.commit()
    conn.close()

def ensure_registros_schema():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='registros'")
    table_exists = cur.fetchone()
    if not table_exists:
        cur.execute("""
            CREATE TABLE registros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empleado_id INTEGER NOT NULL,
                local_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                FOREIGN KEY (empleado_id) REFERENCES empleados(id),
                FOREIGN KEY (local_id) REFERENCES locales(id)
            )
        """)
        conn.commit()
    conn.close()



@app.before_request
def before_request():
   
    if request.path.startswith('/static') or request.path == '/login':
        return
    

    token = get_token_from_request()
    if token:
        payload = verify_jwt_token(token)
        if payload:
            session['role'] = payload['role']
            session['user_id'] = payload['user_id']
            session['username'] = payload['username']

def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            token = get_token_from_request()
            if not token:
                if request.path.startswith('/api/'):
                    return jsonify({"ok": False, "error": "No autorizado"}), 401
                return redirect(url_for("login"))

            payload = verify_jwt_token(token)
            if not payload or payload.get('role') != role:
                if request.path.startswith('/api/'):
                    return jsonify({"ok": False, "error": "No autorizado"}), 403
                return redirect(url_for("login"))

            session['role'] = payload['role']
            session['user_id'] = payload['user_id']
            session['username'] = payload['username']

            return view(*args, **kwargs)
        return wrapped_view
    return decorator

login_required = role_required("admin")

def get_smtp_settings():
    settings = {
        "admin_email": (ADMIN_EMAIL or "").strip(),
        "smtp_host": (SMTP_HOST or "").strip() or "smtp.gmail.com",
        "smtp_port": SMTP_PORT,
        "smtp_security": (SMTP_SECURITY or "ssl").strip().lower(),
        "smtp_email": (SMTP_EMAIL or "").strip(),
        "smtp_password": SMTP_APP_PASSWORD or "",
    }

    try:
        conn = get_db()
        row = conn.execute(
            """
            SELECT email, smtp_host, smtp_port, smtp_security, smtp_email, smtp_password, admin_email_destino, sendgrid_api_key
            FROM admins
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()
        conn.close()

                # if row:
        #     if row["email"]:
        #         settings["admin_email"] = row["email"].strip()
        #     if row["admin_email_destino"]:
        #         settings["admin_email"] = row["admin_email_destino"].strip()
        #     if row["smtp_host"]:
        #         settings["smtp_host"] = row["smtp_host"].strip()
        #     if row["smtp_port"]:
        #         settings["smtp_port"] = row["smtp_port"]
        #     if row["smtp_security"]:
        #         settings["smtp_security"] = row["smtp_security"].strip().lower()
        #     if row["smtp_email"]:
        #         settings["smtp_email"] = row["smtp_email"].strip()
        #     if row["smtp_password"]:
        #         settings["smtp_password"] = row["smtp_password"]
        #     if row["sendgrid_api_key"]:
        #         settings["sendgrid_api_key"] = row["sendgrid_api_key"].strip()
        

        campos = [  
            "email","smtp_host","smtp_port","smtp_security",
            "smtp_email","smtp_password","admin_email_destino",
            "sendgrid_api_key"
        ]   
        
        for campo in campos:
            valor = row[campo]
            if valor is not None and valor != "":
                valor = valor.strip()
                settings[campo] = valor
        
        if settings.get("smtp_security"):
            settings["smtp_security"] = settings["smtp_security"].lower()



    except Exception:
        pass

    try:
        settings["smtp_port"] = int(settings["smtp_port"])
    except (TypeError, ValueError):
        settings["smtp_port"] = 465

    if settings["smtp_security"] not in {"ssl", "starttls"}:
        settings["smtp_security"] = "ssl"

    return settings


def enviar_correo(asunto, cuerpo):
    import requests

    settings = get_smtp_settings()
    mailgun_api_key = settings.get("sendgrid_api_key", "")  # Reutilizamos el campo para Mailgun API Key
    admin_email = settings["admin_email"]

    if not mailgun_api_key or not admin_email:
        error_message = "Falta configurar API Key de Mailgun o correo destino del admin"
        print(f"Correo no configurado: {error_message}. Registro guardado sin enviar email.")
        return {
            "ok": False,
            "status": "not_configured",
            "message": error_message,
        }

    try:
        # Usar sandbox de Mailgun para pruebas
        url = "https://api.mailgun.net/v3/sandboxXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX.mailgun.org/messages"
        
        # Si tienes tu dominio de Mailgun, usa:
        # url = "https://api.mailgun.net/v3/YOUR_DOMAIN/messages"
        
        response = requests.post(
            url,
            auth=("api", mailgun_api_key),
            data={
                "from": "noreply@appqr-g3ft.onrender.com",
                "to": admin_email,
                "subject": asunto,
                "text": cuerpo
            },
            timeout=30
        )

        print(f"Mailgun response status: {response.status_code}")
        if response.status_code >= 200 and response.status_code < 300:
            return {
                "ok": True,
                "status": "sent",
                "message": "Correo enviado",
            }
        else:
            return {
                "ok": False,
                "status": "error",
                "message": f"Mailgun error: {response.status_code} - {response.text}",
            }
    except Exception as e:
        print(f"Error enviando correo con Mailgun: {e}")
        import traceback
        traceback.print_exc()
        return {
            "ok": False,
            "status": "error",
            "message": str(e),
        }

# Función deshabilitada - ya no se generan QRs estáticos para locales
# def generar_qr_files():
#     QR_DIR.mkdir(parents=True, exist_ok=True)
#     conn = get_db()
#     locales = conn.execute("SELECT id, nombre, qr_token FROM locales").fetchall()
#     conn.close()
#
#     for local in locales:
#         qr_url = f"{BASE_URL}/scan/{local['qr_token']}"
#         img = qrcode.make(qr_url)
#         img.save(QR_DIR / f"local_{local['id']}.png")


def generar_pdf_qrs():
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet
    except Exception as e:
        print("No se pudo generar PDF. Instala reportlab:", e)
        return None

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = PDF_DIR / "qrs_locales.pdf"

    conn = get_db()
    locales = conn.execute("SELECT id, nombre, qr_token FROM locales ORDER BY id ASC").fetchall()
    conn.close()

    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Códigos QR de Locales", styles["Title"]))
    story.append(Paragraph("Imprime estas hojas y pega cada QR en su local correspondiente.", styles["Normal"]))
    story.append(Spacer(1, 20))

    for i, local in enumerate(locales):
        qr_path = QR_DIR / f"local_{local['id']}.png"
        story.append(Paragraph(f"Local: {local['nombre']}", styles["Heading1"]))
        story.append(Paragraph(f"Token: {local['qr_token']}", styles["Normal"]))
        story.append(Spacer(1, 12))

        if qr_path.exists():
            story.append(Image(str(qr_path), width=260, height=260))

        if i < len(locales) - 1:
            story.append(PageBreak())

    doc.build(story)
    return pdf_path

@app.route("/")
def home():
    if session.get("role") == "admin":
        return redirect("/admin")
    if session.get("role") == "user":
        return redirect("/scanner")
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    conn = get_db()
    empleados = conn.execute("SELECT * FROM empleados ORDER BY nombre ASC").fetchall()
    conn.close()

    if request.method == "POST":
        login_type = request.form.get("login_type")

        if login_type == "admin":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            conn = get_db()
            admin = conn.execute(
                "SELECT * FROM admins WHERE username = ? AND password_hash = ?",
                (username, hash_password(password))
            ).fetchone()
            conn.close()

            if admin:
                token = generate_jwt_token("admin", admin["id"], admin["username"])
                response = redirect("/admin")
                response.set_cookie('jwt_token', token, max_age=60*60*24*7, httponly=False)
                return response

            error = "Usuario o contraseña incorrectos"

        elif login_type == "user":
            empleado_id = request.form.get("empleado_id")
            if not empleado_id:
                error = "Debes seleccionar un empleado para iniciar sesión"
            else:
                conn = get_db()
                empleado = conn.execute("SELECT * FROM empleados WHERE id = ?", (empleado_id,)).fetchone()
                conn.close()
                if not empleado:
                    error = "Empleado no válido"
                else:
                    token = generate_jwt_token("user", empleado["id"], empleado["nombre"])
                    response = redirect("/scanner")
                    response.set_cookie('jwt_token', token, max_age=60*60*24*7, httponly=False)
                    return response

        else:
            error = "Selecciona un tipo de inicio de sesión válido"

    return render_template("login.html", error=error, empleados=empleados)

@app.route("/logout")
def logout():
    response = redirect("/login")
    response.delete_cookie('jwt_token')
    session.clear()
    return response


@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    error = None
    success = None
    conn = get_db()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "create_employee":
            nombre_empleado = request.form.get("nombre_empleado", "").strip()
            if not nombre_empleado:
                error = "Debes ingresar el nombre del empleado"
            else:
                conn.execute("INSERT INTO empleados (nombre) VALUES (?)", (nombre_empleado,))
                conn.commit()
                success = "Empleado creado correctamente"

    registros = conn.execute('''
        SELECT registros.id, empleados.nombre AS empleado, locales.nombre AS local, registros.fecha
        FROM registros
        JOIN empleados ON registros.empleado_id = empleados.id
        JOIN locales ON registros.local_id = locales.id
        ORDER BY registros.fecha DESC
        LIMIT 50
    ''').fetchall()

    # Obtener QRs generados recientes (solo visibles)
    qrs_generados = conn.execute('''
        SELECT id, nombre_local, nombre_empleado, fecha, hora, token, creado_en, qr_imagen
        FROM qrs_generados
        WHERE visible = 1
        ORDER BY creado_en DESC
        LIMIT 10
    ''').fetchall()

    # Ya no generamos archivos de imagen - usamos las imágenes de la base de datos

    conn.close()

    return render_template(
        "admin.html",
        registros=registros,
        qrs_generados=qrs_generados,
        error=error,
        success=success
    )

@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    # Versión demo - configuración bloqueada
    conn = get_db()
    registros = conn.execute('''
        SELECT registros.id, empleados.nombre AS empleado, locales.nombre AS local, registros.fecha
        FROM registros
        JOIN empleados ON registros.empleado_id = empleados.id
        JOIN locales ON registros.local_id = locales.id
        ORDER BY registros.fecha DESC
        LIMIT 50
    ''').fetchall()

    qrs_generados = conn.execute('''
        SELECT id, nombre_local, nombre_empleado, fecha, hora, token, creado_en, qr_imagen
        FROM qrs_generados
        WHERE visible = 1
        ORDER BY creado_en DESC
        LIMIT 10
    ''').fetchall()

    conn.close()

    return render_template(
        "admin.html",
        registros=registros,
        qrs_generados=qrs_generados,
        error="Configuración bloqueada en versión demo",
        success=None
    )

@app.route("/descargar-registros")
@login_required
def descargar_registros():
    try:
        excel_file = save_excel()
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'registros_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
    except Exception as e:
        return f"Error al generar Excel: {str(e)}", 500

@app.route("/descargar-qrs")
@login_required
def descargar_qrs():
    # generar_qr_files()
    # pdf_path = generar_pdf_qrs()

    # if not pdf_path or not pdf_path.exists():
    #     return "No se pudo generar PDF. Revisa que reportlab esté instalado.", 500

    # return send_file(pdf_path, as_attachment=True)
    return render_template("404Pdf.html")

@app.route("/scanner")
def scanner():
    conn = get_db()
    empleados = conn.execute("SELECT * FROM empleados ORDER BY nombre ASC").fetchall()
    conn.close()
    return render_template(
        "scanner.html",
        empleados=empleados,
        selected_user_id=session.get("user_id"),
        selected_user_name=session.get("username"),
        role=session.get("role")
    )

@app.route("/scan/<token>")
def scan_token(token):
    conn = get_db()
    local = conn.execute("SELECT * FROM locales WHERE qr_token = ?", (token,)).fetchone()

    if not local:
        conn.close()
        return "QR inválido", 404

    # Si el usuario está logueado como empleado, registrar automáticamente
    if session.get("role") == "user" and session.get("user_id"):
        empleado_id = session.get("user_id")
        empleado = conn.execute("SELECT * FROM empleados WHERE id = ?", (empleado_id,)).fetchone()

        if empleado:
            fecha = get_mexico_time()

            # Registrar en historial
            conn.execute(
                "INSERT INTO registros (empleado_id, local_id, fecha) VALUES (?, ?, ?)",
                (empleado_id, local["id"], fecha)
            )
            conn.commit()
            conn.close()

            # Enviar correo
            asunto = "Nuevo registro de asistencia/recolección"
            cuerpo = f"{empleado['nombre']} registró llegada/recolección en {local['nombre']} el {fecha}."
            correo_resultado = enviar_correo(asunto, cuerpo)

            return render_template(
                "registro_exitoso.html",
                mensaje=f"{empleado['nombre']} registró llegada/recolección en {local['nombre']}",
                fecha=fecha,
                correo_enviado=correo_resultado["ok"]
            )

    # Si no está logueado o es admin, mostrar página de confirmación simple
    empleados = conn.execute("SELECT * FROM empleados ORDER BY nombre ASC").fetchall()
    conn.close()

    return render_template(
        "confirmar_simple.html",
        local=local,
        empleados=empleados
    )

@app.route("/scan_qr_generado/<token>")
def scan_qr_generado(token):
    conn = get_db()
    qr_generado = conn.execute("SELECT * FROM qrs_generados WHERE token = ?", (token,)).fetchone()

    if not qr_generado:
        conn.close()
        return "QR inválido", 404

    # Si el usuario está logueado como empleado, registrar automáticamente
    if session.get("role") == "user" and session.get("user_id"):
        empleado_id = session.get("user_id")
        empleado = conn.execute("SELECT * FROM empleados WHERE id = ?", (empleado_id,)).fetchone()

        if empleado:
            fecha = get_mexico_time()

            # Verificar si el local existe, si no, crearlo
            local = conn.execute("SELECT * FROM locales WHERE nombre = ?", (qr_generado["nombre_local"],)).fetchone()

            if not local:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO locales (nombre, qr_token) VALUES (?, ?)",
                    (qr_generado["nombre_local"], token)
                )
                conn.commit()
                local_id = cur.lastrowid
            else:
                local_id = local["id"]

            # Registrar en historial
            conn.execute(
                "INSERT INTO registros (empleado_id, local_id, fecha) VALUES (?, ?, ?)",
                (empleado_id, local_id, fecha)
            )
            conn.commit()
            conn.close()

            # Enviar correo
            asunto = "Nuevo registro de QR personalizado"
            cuerpo = f"{empleado['nombre']} registró QR personalizado: {qr_generado['nombre_local']} - {qr_generado['nombre_empleado']} (Fecha: {qr_generado['fecha']}, Hora: {qr_generado['hora']}) el {fecha}."
            correo_resultado = enviar_correo(asunto, cuerpo)

            return render_template(
                "registro_exitoso.html",
                mensaje=f"{empleado['nombre']} registró QR personalizado: {qr_generado['nombre_local']} - {qr_generado['nombre_empleado']}",
                fecha=fecha,
                correo_enviado=correo_resultado["ok"]
            )

    # Si no está logueado o es admin, mostrar página de confirmación simple
    empleados = conn.execute("SELECT * FROM empleados ORDER BY nombre ASC").fetchall()
    conn.close()

    return render_template(
        "confirmar_qr_generado_simple.html",
        qr_generado=qr_generado,
        empleados=empleados
    )

@app.route("/api/registrar_simple", methods=["POST"])
def api_registrar_simple():
    data = request.get_json()
    empleado_id = data.get("empleado_id")
    qr_token = data.get("qr_token")

    if not empleado_id or not qr_token:
        return jsonify({"ok": False, "error": "Falta empleado o QR"}), 400

    conn = get_db()
    local = conn.execute("SELECT * FROM locales WHERE qr_token = ?", (qr_token,)).fetchone()

    if not local:
        conn.close()
        return jsonify({"ok": False, "error": "QR inválido"}), 404

    empleado = conn.execute("SELECT * FROM empleados WHERE id = ?", (empleado_id,)).fetchone()

    if not empleado:
        conn.close()
        return jsonify({"ok": False, "error": "Empleado inválido"}), 404

    fecha = get_mexico_time()

    conn.execute(
        "INSERT INTO registros (empleado_id, local_id, fecha) VALUES (?, ?, ?)",
        (empleado_id, local["id"], fecha)
    )
    conn.commit()
    conn.close()

    asunto = "Nuevo registro de asistencia/recolección"
    cuerpo = f"{empleado['nombre']} registró llegada/recolección en {local['nombre']} el {fecha}."
    correo_resultado = enviar_correo(asunto, cuerpo)

    return jsonify({
        "ok": True,
        "mensaje": f"{empleado['nombre']} registró llegada/recolección en {local['nombre']}",
        "empleado": empleado["nombre"],
        "local": local["nombre"],
        "fecha": fecha,
        "correo_enviado": correo_resultado["ok"],
        "correo_estado": correo_resultado["status"],
        "correo_mensaje": correo_resultado["message"],
    })

@app.route("/api/registrar", methods=["POST"])
def api_registrar():
    data = request.get_json()
    empleado_id = data.get("empleado_id")
    qr_token = data.get("qr_token")

    if not empleado_id and session.get("role") == "user":
        empleado_id = session.get("user_id")

    if not empleado_id or not qr_token:
        return jsonify({"ok": False, "error": "Falta empleado o QR"}), 400

    conn = get_db()
    local = conn.execute("SELECT * FROM locales WHERE qr_token = ?", (qr_token,)).fetchone()

    if not local:
        conn.close()
        return jsonify({"ok": False, "error": "QR inválido"}), 404

    empleado = conn.execute("SELECT * FROM empleados WHERE id = ?", (empleado_id,)).fetchone()

    if not empleado:
        conn.close()
        return jsonify({"ok": False, "error": "Empleado inválido"}), 404

    fecha = get_mexico_time()

    conn.execute(
        "INSERT INTO registros (empleado_id, local_id, fecha) VALUES (?, ?, ?)",
        (empleado_id, local["id"], fecha)
    )
    conn.commit()
    conn.close()

    asunto = "Nuevo registro de asistencia/recolección"
    cuerpo = f"{empleado['nombre']} registró llegada/recolección en {local['nombre']} el {fecha}."
    correo_resultado = enviar_correo(asunto, cuerpo)

    return jsonify({
        "ok": True,
        "mensaje": f"{empleado['nombre']} registró llegada/recolección en {local['nombre']}",
        "empleado": empleado["nombre"],
        "local": local["nombre"],
        "fecha": fecha,
        "correo_enviado": correo_resultado["ok"],
        "correo_estado": correo_resultado["status"],
        "correo_mensaje": correo_resultado["message"],
    })

@app.route("/api/registrar_qr_generado_simple", methods=["POST"])
def api_registrar_qr_generado_simple():
    data = request.get_json()
    empleado_id = data.get("empleado_id")
    qr_token = data.get("qr_token")

    if not empleado_id or not qr_token:
        return jsonify({"ok": False, "error": "Falta empleado o QR"}), 400

    conn = get_db()
    qr_generado = conn.execute("SELECT * FROM qrs_generados WHERE token = ?", (qr_token,)).fetchone()

    if not qr_generado:
        conn.close()
        return jsonify({"ok": False, "error": "QR inválido"}), 404

    empleado = conn.execute("SELECT * FROM empleados WHERE id = ?", (empleado_id,)).fetchone()

    if not empleado:
        conn.close()
        return jsonify({"ok": False, "error": "Empleado inválido"}), 404

    fecha = get_mexico_time()

    # Insertar en registros usando el nombre del local del QR generado
    # Primero verificamos si el local existe en la tabla locales
    local = conn.execute("SELECT * FROM locales WHERE nombre = ?", (qr_generado["nombre_local"],)).fetchone()

    if not local:
        # Si el local no existe, lo creamos
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO locales (nombre, qr_token) VALUES (?, ?)",
            (qr_generado["nombre_local"], qr_token)
        )
        conn.commit()
        local_id = cur.lastrowid
    else:
        local_id = local["id"]

    conn.execute(
        "INSERT INTO registros (empleado_id, local_id, fecha) VALUES (?, ?, ?)",
        (empleado_id, local_id, fecha)
    )
    conn.commit()
    conn.close()

    asunto = "Nuevo registro de QR personalizado"
    cuerpo = f"{empleado['nombre']} registró QR personalizado: {qr_generado['nombre_local']} - {qr_generado['nombre_empleado']} (Fecha: {qr_generado['fecha']}, Hora: {qr_generado['hora']}) el {fecha}."
    correo_resultado = enviar_correo(asunto, cuerpo)

    return jsonify({
        "ok": True,
        "mensaje": f"{empleado['nombre']} registró QR personalizado: {qr_generado['nombre_local']} - {qr_generado['nombre_empleado']}",
        "empleado": empleado["nombre"],
        "local": qr_generado["nombre_local"],
        "empleado_qr": qr_generado["nombre_empleado"],
        "fecha_qr": qr_generado["fecha"],
        "hora_qr": qr_generado["hora"],
        "fecha": fecha,
        "correo_enviado": correo_resultado["ok"],
        "correo_estado": correo_resultado["status"],
        "correo_mensaje": correo_resultado["message"],
    })

@app.route("/api/registrar_qr_generado", methods=["POST"])
def api_registrar_qr_generado():
    data = request.get_json()
    empleado_id = data.get("empleado_id")
    qr_token = data.get("qr_token")

    if not empleado_id and session.get("role") == "user":
        empleado_id = session.get("user_id")

    if not empleado_id or not qr_token:
        return jsonify({"ok": False, "error": "Falta empleado o QR"}), 400

    conn = get_db()
    qr_generado = conn.execute("SELECT * FROM qrs_generados WHERE token = ?", (qr_token,)).fetchone()

    if not qr_generado:
        conn.close()
        return jsonify({"ok": False, "error": "QR inválido"}), 404

    empleado = conn.execute("SELECT * FROM empleados WHERE id = ?", (empleado_id,)).fetchone()

    if not empleado:
        conn.close()
        return jsonify({"ok": False, "error": "Empleado inválido"}), 404

    fecha = get_mexico_time()

    # Insertar en registros usando el nombre del local del QR generado
    # Primero verificamos si el local existe en la tabla locales
    local = conn.execute("SELECT * FROM locales WHERE nombre = ?", (qr_generado["nombre_local"],)).fetchone()

    if not local:
        # Si el local no existe, lo creamos
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO locales (nombre, qr_token) VALUES (?, ?)",
            (qr_generado["nombre_local"], qr_token)
        )
        conn.commit()
        local_id = cur.lastrowid
    else:
        local_id = local["id"]

    conn.execute(
        "INSERT INTO registros (empleado_id, local_id, fecha) VALUES (?, ?, ?)",
        (empleado_id, local_id, fecha)
    )
    conn.commit()
    conn.close()

    asunto = "Nuevo registro de QR personalizado"
    cuerpo = f"{empleado['nombre']} registró QR personalizado: {qr_generado['nombre_local']} - {qr_generado['nombre_empleado']} (Fecha: {qr_generado['fecha']}, Hora: {qr_generado['hora']}) el {fecha}."
    correo_resultado = enviar_correo(asunto, cuerpo)

    return jsonify({
        "ok": True,
        "mensaje": f"{empleado['nombre']} registró QR personalizado: {qr_generado['nombre_local']} - {qr_generado['nombre_empleado']}",
        "empleado": empleado["nombre"],
        "local": qr_generado["nombre_local"],
        "empleado_qr": qr_generado["nombre_empleado"],
        "fecha_qr": qr_generado["fecha"],
        "hora_qr": qr_generado["hora"],
        "fecha": fecha,
        "correo_enviado": correo_resultado["ok"],
        "correo_estado": correo_resultado["status"],
        "correo_mensaje": correo_resultado["message"],
    })

@app.route("/api/registros")
def api_registros():
    conn = get_db()
    registros = conn.execute('''
        SELECT registros.id, empleados.nombre AS empleado, locales.nombre AS local, registros.fecha
        FROM registros
        JOIN empleados ON registros.empleado_id = empleados.id
        JOIN locales ON registros.local_id = locales.id
        ORDER BY registros.fecha DESC
        LIMIT 20
    ''').fetchall()
    conn.close()

    return jsonify([dict(r) for r in registros])

@app.route("/api/registros/<int:registro_id>", methods=["DELETE"])
@login_required
def delete_registro(registro_id):
    conn = get_db()
    conn.execute("DELETE FROM registros WHERE id = ?", (registro_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "message": "Registro eliminado"})

@app.route("/api/qrs_generados/<int:qr_id>", methods=["DELETE"])
@login_required
def hide_qr_generado(qr_id):
    conn = get_db()
    conn.execute("UPDATE qrs_generados SET visible = 0 WHERE id = ?", (qr_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "message": "QR ocultado del dashboard"})

@app.route("/generar-qr", methods=["GET", "POST"])
@login_required
def generar_qr():
    conn = get_db()
    locales = conn.execute("SELECT id, nombre FROM locales ORDER BY nombre ASC").fetchall()
    empleados = conn.execute("SELECT id, nombre FROM empleados ORDER BY nombre ASC").fetchall()
    
    qr_image = None
    qr_data = None
    qr_token = None
    success = None
    error = None

    if request.method == "POST":
        nombre_local = request.form.get("nombre_local", "").strip()
        nombre_empleado = request.form.get("nombre_empleado", "").strip()
        fecha = request.form.get("fecha", "").strip()
        hora = request.form.get("hora", "").strip()

        if nombre_local and nombre_empleado and fecha and hora:
            # Verificar límite de 10 QRs
            qr_count = conn.execute("SELECT COUNT(*) FROM qrs_generados WHERE visible = 1").fetchone()[0]
            if qr_count >= 10:
                error = "Límite de 10 QRs alcanzado. Esta es una versión demo."
                qr_image = None
            else:
                qr_token = hashlib.sha256(f"{nombre_local}{nombre_empleado}{fecha}{hora}{get_mexico_datetime().timestamp()}".encode()).hexdigest()[:12].upper()
                qr_url = f"{BASE_URL}/scan_qr_generado/{qr_token}"

                try:
                    import io
                    import base64

                    img = qrcode.make(qr_url)
                    img_io = io.BytesIO()
                    img.save(img_io, 'PNG')
                    img_io.seek(0)
                    qr_image = base64.b64encode(img_io.getvalue()).decode()

                    # Guardar en BD
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO qrs_generados (nombre_local, nombre_empleado, fecha, hora, token, admin_id, creado_en, visible, qr_imagen)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                    """, (nombre_local, nombre_empleado, fecha, hora, qr_token, session.get("admin_id"), get_mexico_datetime(), qr_image))
                    conn.commit()
                    return redirect("/admin")

                except Exception as e:
                    error = f"Error al generar QR: {str(e)}"
                    qr_image = None

    conn.close()

    return render_template(
        "generar_qr.html",
        locales=locales,
        empleados=empleados,
        qr_image=qr_image,
        qr_data=qr_data,
        qr_token=qr_token,
        success=success,
        error=error
    )

if __name__ == "__main__":
    # Ensure DB schema is up-to-date (add admin.email if missing)
    try:
        ensure_admin_schema()
    except Exception:
        pass
    
    # Ensure qrs_generados table exists
    try:
        ensure_qrs_generados_schema()
    except Exception:
        pass
    
    # Ensure registros table exists
    try:
        ensure_registros_schema()
    except Exception:
        pass

    # generar_qr_files()  # Deshabilitado - ya no se generan QRs estáticos para locales
    generar_pdf_qrs()
    app.run(host = "0.0.0.0", port =5000, debug=True)
 