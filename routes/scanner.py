import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Blueprint, render_template, request, session
from models.database import get_db
from utils.helpers import get_mexico_time

scanner_bp = Blueprint('scanner', __name__)

@scanner_bp.route("/scanner")
def scanner():
    db = get_db()
    response = db.table('empleado').select('*').order('nombre').execute()
    empleados = response.data
    return render_template(
        "scanner.html",
        empleados=empleados,
        selected_user_id=session.get("user_id"),
        selected_user_name=session.get("username"),
        role=session.get("role")
    )

@scanner_bp.route("/scan/<token>")
def scan_token(token):
    import time
    db = get_db()
    
    # Intentar con reintentos
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = db.table('locales').select('*').eq('qr_token', token).execute()
            locales = response.data
            break
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            else:
                return f"Error de conexión con Supabase: {str(e)}", 500
    
    if not locales:
        return "QR inválido", 404
    
    local = locales[0]

    # Si el usuario está logueado como empleado, registrar automáticamente
    if session.get("role") == "user" and session.get("user_id"):
        empleado_id = session.get("user_id")
        response = db.table('empleado').select('*').eq('id', empleado_id).execute()
        empleados = response.data
        
        if empleados:
            empleado = empleados[0]
            fecha = get_mexico_time()

            # Registrar en historial
            db.table('registros_asistencia').insert({
                'empleado_id': empleado_id,
                'locales_id': local['id'],
                'fecha_hora': fecha
            }).execute()

            return render_template(
                "registro_exitoso.html",
                mensaje=f"{empleado['nombre']} registró llegada/recolección en {local['nombre_local']}",
                fecha=fecha,
                correo_enviado=False
            )

    # Si no está logueado o es admin, mostrar página de confirmación simple
    response = db.table('empleado').select('*').order('nombre').execute()
    empleados = response.data

    return render_template(
        "confirmar_simple.html",
        local=local,
        empleados=empleados
    )

@scanner_bp.route("/scan_qr_generado/<token>")
def scan_qr_generado(token):
    from config import BASE_URL, ENVIRONMENT
    db = get_db()
    
    # Intentar con reintentos
    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = db.table('qr_tokens').select('*').eq('token', token).execute()
            qrs = response.data
            break
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            else:
                return f"Error de conexión con Supabase: {str(e)}", 500
    
    if not qrs:
        return "QR inválido", 404
    
    qr_generado = qrs[0]

    # Si el usuario está logueado como empleado, registrar automáticamente
    if session.get("role") == "user" and session.get("user_id"):
        empleado_id = session.get("user_id")
        response = db.table('empleado').select('*').eq('id', empleado_id).execute()
        empleados = response.data
        
        if empleados:
            empleado = empleados[0]
            fecha = get_mexico_time()

            # Verificar si el local existe, si no, crearlo
            response = db.table('locales').select('*').eq('nombre_local', qr_generado['nombre_local']).execute()
            locales = response.data
            
            if not locales:
                # Crear local
                new_local = db.table('locales').insert({
                    'nombre_local': qr_generado['nombre_local'],
                    'qr_token': token
                }).execute()
                local_id = new_local.data[0]['id']
            else:
                local_id = locales[0]['id']

            # Registrar en historial
            observaciones = request.form.get('observaciones', '').strip()
            db.table('registros_asistencia').insert({
                'empleado_id': empleado_id,
                'locales_id': local_id,
                'fecha_hora': fecha,
                'observaciones': observaciones,
                'token_id': qr_generado['id']
            }).execute()

            return render_template(
                "registro_exitoso.html",
                mensaje=f"{empleado['nombre']} registró QR personalizado: {qr_generado['nombre_local']} - {qr_generado['nombre_empleado']}",
                fecha=fecha,
                correo_enviado=False
            )

    # Si no está logueado o es admin, mostrar página de confirmación simple
    response = db.table('empleado').select('*').order('nombre').execute()
    empleados = response.data

    return render_template(
        "confirmar_qr_generado_simple.html",
        qr_generado=qr_generado,
        empleados=empleados
    )
