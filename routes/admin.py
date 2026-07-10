import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from flask import Blueprint, render_template, request, redirect, session, send_file, jsonify
from datetime import datetime
from models.database import get_db
from services.qr_service import save_excel
from services.qr_service import generate_qr_token, generate_qr_image
from utils.decorators import login_required


admin_bp = Blueprint('admin', __name__)

@admin_bp.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    error = None
    success = None
    db = get_db()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "create_employee":
            nombre_empleado = request.form.get("nombre_empleado", "").strip()
            if not nombre_empleado:
                error = "Debes ingresar el nombre del empleado"
            else:
                db.table('empleado').insert({'nombre': nombre_empleado}).execute()
                success = "Empleado creado correctamente"

    # Obtener registros con reintentos
    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = db.table('registros_asistencia').select('''
                id,
                empleado_id,
                locales_id,
                fecha_hora
            ''').order('fecha_hora', desc=True).limit(50).execute()
            registros_raw = response.data
            break
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)
                continue
            else:
                registros_raw = []
    
    # Obtener todos los empleados y locales de una sola vez
    empleados_dict = {}
    locales_dict = {}
    
    try:
        emp_response = db.table('empleado').select('id, nombre').execute()
        empleados_dict = {emp['id']: emp['nombre'] for emp in emp_response.data}
        print(f"Empleados cargados: {len(empleados_dict)}, IDs: {list(empleados_dict.keys())}")
    except Exception as e:
        print(f"Error al obtener empleados: {str(e)}")
    
    try:
        local_response = db.table('locales').select('id, nombre_local').execute()
        locales_dict = {loc['id']: loc['nombre_local'] for loc in local_response.data}
        print(f"Locales cargados: {len(locales_dict)}, IDs: {list(locales_dict.keys())}")
    except Exception as e:
        print(f"Error al obtener locales: {str(e)}")
    
    # Obtener datos relacionados usando los diccionarios
    registros = []
    for reg in registros_raw:
        print(f"Registro: empleado_id={reg['empleado_id']}, locales_id={reg['locales_id']}")
        empleado_nombre = empleados_dict.get(reg['empleado_id'], 'Desconocido')
        local_nombre = locales_dict.get(reg['locales_id'], 'Desconocido')
        
        registros.append({
            'id': reg['id'],
            'empleado': empleado_nombre,
            'local': local_nombre,
            'fecha': reg['fecha_hora']
        })

    # Mostrar solo los QRs mas recientes en el dashboard.
    qr_tokens = []
    for attempt in range(max_retries):
        try:
            response = db.table('qr_tokens').select('*').order('id', desc=True).limit(5).execute()
            qr_tokens = response.data
            break
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)
                continue
            else:
                qr_tokens = []

    return render_template(
        "admin.html",
        registros=registros,
        qr_tokens=qr_tokens,
        error=error,
        success=success
    )

@admin_bp.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    db = get_db()
    error = None
    success = None
    
    # Obtener admin actual
    admin_id = session.get("user_id")
    response = db.table('admin').select('*').eq('id', admin_id).execute()
    admin = response.data[0] if response.data else None
    admin_username = admin['nombre'] if admin else ''
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "save":
            new_username = request.form.get("new_admin_username", "").strip()
            current_password = request.form.get("current_password", "").strip()
            new_password = request.form.get("new_password", "").strip()
            confirm_password = request.form.get("confirm_password", "").strip()
            
            # Verificar contraseña actual
            if current_password and admin and admin['password'] != current_password:
                error = "La contraseña actual es incorrecta"
            elif new_password and new_password != confirm_password:
                error = "Las nuevas contraseñas no coinciden"
            else:
                # Actualizar datos
                update_data = {'nombre': new_username}
                if new_password:
                    update_data['password'] = new_password
                
                db.table('admin').update(update_data).eq('id', admin_id).execute()
                
                # Actualizar sesión
                session["username"] = new_username
                
                # Regenerar token
                from services.auth_service import generate_jwt_token
                token = generate_jwt_token("admin", admin_id, new_username)
                response = redirect("/admin/settings")
                response.set_cookie('jwt_token', token, max_age=60*60*24*7, httponly=False)
                return response
    
    # Obtener registros con joins
    response = db.table('registros_asistencia').select('''
        id,
        empleado_id,
        locales_id,
        fecha_hora
    ''').order('fecha_hora', desc=True).limit(50).execute()
    registros_raw = response.data
    
    # Obtener todos los empleados y locales de una sola vez
    empleados_dict = {}
    locales_dict = {}
    
    try:
        emp_response = db.table('empleado').select('id, nombre').execute()
        empleados_dict = {emp['id']: emp['nombre'] for emp in emp_response.data}
    except Exception as e:
        print(f"Error al obtener empleados: {str(e)}")
    
    try:
        local_response = db.table('locales').select('id, nombre_local').execute()
        locales_dict = {loc['id']: loc['nombre_local'] for loc in local_response.data}
    except Exception as e:
        print(f"Error al obtener locales: {str(e)}")
    
    # Obtener datos relacionados usando los diccionarios
    registros = []
    for reg in registros_raw:
        empleado_nombre = empleados_dict.get(reg['empleado_id'], 'Desconocido')
        local_nombre = locales_dict.get(reg['locales_id'], 'Desconocido')
        
        registros.append({
            'id': reg['id'],
            'empleado': empleado_nombre,
            'local': local_nombre,
            'fecha': reg['fecha_hora']
        })

    # Obtener QRs generados recientes
    qr_tokens = []
    for attempt in range(max_retries):
        try:
            response = db.table('qr_tokens').select('*').order('id', desc=True).limit(10).execute()
            qr_tokens = response.data
            break
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)
                continue
            else:
                qr_tokens = []

    return render_template(
        "admin_settings.html",
        registros=registros,
        qr_tokens=qr_tokens,
        admin_username=admin_username,
        error=error,
        success=success
    )

@admin_bp.route("/descargar-registros")
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

@admin_bp.route("/descargar-qrs")
@login_required
def descargar_qrs():
    return render_template("404Pdf.html")

@admin_bp.route("/generar-qr", methods=["GET", "POST"])
@login_required
def generar_qr():
    from config import BASE_URL
    db = get_db()
    
    response = db.table('locales').select('id, nombre_local').order('nombre_local').execute()
    locales = response.data
    
    response = db.table('empleado').select('id, nombre').order('nombre').execute()
    empleados = response.data
    
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
            qr_token = generate_qr_token(nombre_local, nombre_empleado, fecha, hora)
            qr_url = f"{BASE_URL}/scan_qr_generado/{qr_token}"

            try:
                qr_image = generate_qr_image(qr_url)

                # Guardar en BD
                insert_data = {
                    'nombre_local': nombre_local,
                    'nombre_empleado': nombre_empleado,
                    'fecha': fecha,
                    'hora': hora,
                    'token': qr_token,
                    'qr_imagen': qr_image
                }
                result = db.table('qr_tokens').insert(insert_data).execute()
                return redirect("/admin")

            except Exception as e:
                error = f"Error al generar QR: {str(e)}"
                qr_image = None

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