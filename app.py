from flask import Flask, render_template, request, redirect, jsonify, send_file, session, url_for
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import smtplib
from email.message import EmailMessage
import os
import qrcode
import hashlib
import jwt
from functools import wraps

app = Flask(__name__)

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
                visible INTEGER DEFAULT 1
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
    conn.close()


# Some Flask versions may not expose `before_first_request` as an attribute in this environment.
# Call schema migration at startup instead of using the decorator.

@app.before_request
def before_request():
    # Skip token loading for static files and login page
    if request.path.startswith('/static') or request.path == '/login':
        return
    
    # Load JWT token into session for template compatibility
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
                return redirect(url_for("login"))
            
            payload = verify_jwt_token(token)
            if not payload or payload.get('role') != role:
                return redirect(url_for("login"))
            
            # Update session with token data for template compatibility
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
            SELECT email, smtp_host, smtp_port, smtp_security, smtp_email, smtp_password
            FROM admins
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()
        conn.close()

        if row:
            if row["email"]:
                settings["admin_email"] = row["email"].strip()
            if row["admin_email_destino"]:
                settings["admin_email"] = row["admin_email_destino"].strip()
            if row["smtp_host"]:
                settings["smtp_host"] = row["smtp_host"].strip()
            if row["smtp_port"]:
                settings["smtp_port"] = row["smtp_port"]
            if row["smtp_security"]:
                settings["smtp_security"] = row["smtp_security"].strip().lower()
            if row["smtp_email"]:
                settings["smtp_email"] = row["smtp_email"].strip()
            if row["smtp_password"]:
                settings["smtp_password"] = row["smtp_password"]
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
    settings = get_smtp_settings()
    admin_email = settings["admin_email"]
    smtp_email = settings["smtp_email"]
    smtp_password = settings["smtp_password"]
    smtp_host = settings["smtp_host"]
    smtp_port = settings["smtp_port"]
    smtp_security = settings["smtp_security"]

    if not smtp_email or not smtp_password or not admin_email:
        error_message = "Falta configurar correo emisor, clave SMTP o correo destino del admin"
        print(f"Correo no configurado: {error_message}. Registro guardado sin enviar email.")
        return {
            "ok": False,
            "status": "not_configured",
            "message": error_message,
        }

    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = smtp_email
    msg["To"] = admin_email
    msg.set_content(cuerpo)

    try:
        if smtp_security == "starttls":
            with smtplib.SMTP(smtp_host, smtp_port) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(smtp_email, smtp_password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp:
                smtp.login(smtp_email, smtp_password)
                smtp.send_message(msg)
        return {
            "ok": True,
            "status": "sent",
            "message": "Correo enviado",
        }
    except Exception as e:
        print(f"Error enviando correo: {e}")
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
        SELECT id, nombre_local, nombre_empleado, fecha, hora, token, creado_en
        FROM qrs_generados
        WHERE visible = 1
        ORDER BY creado_en DESC
        LIMIT 10
    ''').fetchall()

    # Generar imágenes de QRs personalizados (siempre regenerar con URL correcta)
    for qr in qrs_generados:
        qr_path = QR_DIR / f"qr_generado_{qr['id']}.png"
        qr_url = f"{BASE_URL}/scan_qr_generado/{qr['token']}"
        img = qrcode.make(qr_url)
        img.save(qr_path)

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
    error = None
    success = None
    conn = get_db()
    admin_row = conn.execute("SELECT * FROM admins WHERE id = ?", (session["user_id"],)).fetchone()

    if request.method == "POST":
        action = request.form.get("action", "save")
        new_username = request.form.get("new_admin_username", "").strip()
        new_email = request.form.get("admin_email", "").strip()
        smtp_host = request.form.get("smtp_host", "").strip()
        smtp_port_raw = request.form.get("smtp_port", "").strip()
        smtp_security = request.form.get("smtp_security", "ssl").strip().lower()
        smtp_email = request.form.get("smtp_email", "").strip()
        smtp_password = request.form.get("smtp_password", "")
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if admin_row is None:
            error = "No se encontró el usuario administrador"
        else:
            smtp_port = None
            if smtp_port_raw:
                try:
                    smtp_port = int(smtp_port_raw)
                    if smtp_port <= 0:
                        raise ValueError()
                except ValueError:
                    error = "El puerto SMTP debe ser un número válido"

            if not error and smtp_security not in {"ssl", "starttls"}:
                error = "Selecciona un tipo de seguridad SMTP válido"

            if new_username and new_username != admin_row["username"]:
                existing = conn.execute("SELECT id FROM admins WHERE username = ?", (new_username,)).fetchone()
                if existing:
                    error = "El nombre de usuario ya está en uso"
                else:
                    conn.execute("UPDATE admins SET username = ? WHERE id = ?", (new_username, session["user_id"]))
                    session["username"] = new_username
                    success = "Usuario administrador actualizado"
            if not error and new_password:
                if not current_password:
                    error = "Ingresa tu contraseña actual para cambiar la contraseña"
                elif hash_password(current_password) != admin_row["password_hash"]:
                    error = "Contraseña actual incorrecta"
                elif new_password != confirm_password:
                    error = "La nueva contraseña y su confirmación no coinciden"
                else:
                    conn.execute("UPDATE admins SET password_hash = ? WHERE id = ?", (hash_password(new_password), session["user_id"]))
                    success = "Contraseña actualizada correctamente"
            current_email = admin_row["email"] if "email" in admin_row.keys() else ""
            if not error and new_email != current_email:
                conn.execute("UPDATE admins SET email = ? WHERE id = ?", (new_email, session["user_id"]))
                success = "Datos de administrador actualizados"
            current_smtp_host = admin_row["smtp_host"] if "smtp_host" in admin_row.keys() and admin_row["smtp_host"] else ""
            current_smtp_port = admin_row["smtp_port"] if "smtp_port" in admin_row.keys() and admin_row["smtp_port"] else None
            current_smtp_security = admin_row["smtp_security"] if "smtp_security" in admin_row.keys() and admin_row["smtp_security"] else "ssl"
            current_smtp_email = admin_row["smtp_email"] if "smtp_email" in admin_row.keys() and admin_row["smtp_email"] else ""
            current_smtp_password = admin_row["smtp_password"] if "smtp_password" in admin_row.keys() and admin_row["smtp_password"] else ""
            current_admin_email_destino = admin_row["admin_email_destino"] if "admin_email_destino" in admin_row.keys() and admin_row["admin_email_destino"] else ""

            smtp_changed = (
                smtp_host != current_smtp_host
                or smtp_port != current_smtp_port
                or smtp_security != current_smtp_security
                or smtp_email != current_smtp_email
                or bool(smtp_password)
            )
            admin_email_destino = request.form.get("admin_email_destino", "").strip()
            email_destino_changed = admin_email_destino != current_admin_email_destino

            if not error and smtp_changed:
                conn.execute(
                    """
                    UPDATE admins
                    SET smtp_host = ?, smtp_port = ?, smtp_security = ?, smtp_email = ?, smtp_password = ?
                    WHERE id = ?
                    """,
                    (
                        smtp_host,
                        smtp_port,
                        smtp_security,
                        smtp_email,
                        smtp_password if smtp_password else current_smtp_password,
                        session["user_id"],
                    )
                )
                success = "Configuración de correo actualizada"

            if not error and email_destino_changed:
                conn.execute("UPDATE admins SET admin_email_destino = ? WHERE id = ?", (admin_email_destino, session["user_id"]))
                conn.commit()
                if success:
                    success += " y correo destino actualizado"
                else:
                    success = "Correo destino actualizado"

            if not error:
                conn.commit()
                admin_row = conn.execute("SELECT * FROM admins WHERE id = ?", (session["user_id"],)).fetchone()
                if action == "test_smtp":
                    test_subject = "Prueba de configuracion SMTP"
                    test_body = (
                        f"Hola {session.get('username', 'admin')},\n\n"
                        "Este es un correo de prueba enviado desde la configuracion de la app.\n"
                        "Si recibiste este mensaje, la configuracion SMTP esta funcionando.\n"
                    )
                    correo_resultado = enviar_correo(test_subject, test_body)
                    if correo_resultado["ok"]:
                        success = "Correo de prueba enviado correctamente"
                    else:
                        error = f"No se pudo enviar el correo de prueba: {correo_resultado['message']}"

    admin_email = admin_row["email"] if admin_row and "email" in admin_row.keys() else ""
    admin_username = admin_row["username"] if admin_row else ""
    smtp_host_value = admin_row["smtp_host"] if admin_row and "smtp_host" in admin_row.keys() and admin_row["smtp_host"] else SMTP_HOST
    smtp_port_value = admin_row["smtp_port"] if admin_row and "smtp_port" in admin_row.keys() and admin_row["smtp_port"] else SMTP_PORT
    smtp_security_value = admin_row["smtp_security"] if admin_row and "smtp_security" in admin_row.keys() and admin_row["smtp_security"] else SMTP_SECURITY
    smtp_email_value = admin_row["smtp_email"] if admin_row and "smtp_email" in admin_row.keys() and admin_row["smtp_email"] else SMTP_EMAIL
    admin_email_destino_value = admin_row["admin_email_destino"] if admin_row and "admin_email_destino" in admin_row.keys() and admin_row["admin_email_destino"] else ADMIN_EMAIL
    conn.close()

    return render_template(
        "admin_settings.html",
        admin_email=admin_email,
        admin_username=admin_username,
        smtp_host=smtp_host_value,
        smtp_port=smtp_port_value,
        smtp_security=smtp_security_value,
        smtp_email=smtp_email_value,
        admin_email_destino=admin_email_destino_value,
        error=error,
        success=success
    )

@app.route("/descargar-qrs")
@login_required
def descargar_qrs():
    generar_qr_files()
    pdf_path = generar_pdf_qrs()

    if not pdf_path or not pdf_path.exists():
        return "No se pudo generar PDF. Revisa que reportlab esté instalado.", 500

    return send_file(pdf_path, as_attachment=True)

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
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
            qr_token = hashlib.sha256(f"{nombre_local}{nombre_empleado}{fecha}{hora}{datetime.now().timestamp()}".encode()).hexdigest()[:12].upper()
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
                    INSERT INTO qrs_generados (nombre_local, nombre_empleado, fecha, hora, token, admin_id, creado_en, visible)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """, (nombre_local, nombre_empleado, fecha, hora, qr_token, session.get("admin_id"), datetime.now()))
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

    # generar_qr_files()  # Deshabilitado - ya no se generan QRs estáticos para locales
    generar_pdf_qrs()
    app.run(host = "0.0.0.0", port =5000, debug=True)
