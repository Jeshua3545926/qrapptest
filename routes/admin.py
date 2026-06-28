import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Blueprint, render_template, request, redirect, session, send_file, jsonify
from datetime import datetime
from models.database import get_db
from services.qr_service import save_excel
from services.qr_service import generate_qr_token, generate_qr_image
from utils.decorators import login_required
from utils.helpers import get_mexico_datetime
import base64
import io

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

    # Obtener registros con joins
    response = db.table('registros_asistencia').select('''
        id,
        empleado_id,
        locales_id,
        fecha_hora
    ''').order('fecha_hora', desc=True).limit(50).execute()
    registros_raw = response.data
    
    # Obtener datos relacionados manualmente
    registros = []
    for reg in registros_raw:
        emp_response = db.table('empleado').select('nombre').eq('id', reg['empleado_id']).execute()
        local_response = db.table('locales').select('nombre_local').eq('id', reg['locales_id']).execute()
        
        empleado_nombre = emp_response.data[0]['nombre'] if emp_response.data else 'Desconocido'
        local_nombre = local_response.data[0]['nombre_local'] if local_response.data else 'Desconocido'
        
        registros.append({
            'id': reg['id'],
            'empleado': empleado_nombre,
            'local': local_nombre,
            'fecha': reg['fecha_hora']
        })

    # Mostrar solo los QRs mas recientes en el dashboard.
    response = db.table('qr_tokens').select('*').order('id', desc=True).limit(5).execute()
    qr_tokens = response.data

    return render_template(
        "admin.html",
        registros=registros,
        qr_tokens=qr_tokens,
        error=error,
        success=success
    )

@admin_bp.route("/admin/qrs")
@login_required
def admin_qrs():
    db = get_db()

    response = db.table('qr_tokens').select(
        'id, nombre_local, nombre_empleado, fecha, hora, token'
    ).order('id', desc=True).execute()

    count_response = db.table('qr_tokens').select(
        'id',
        count='exact'
    ).execute()

    qr_tokens = response.data or []
    total_qr = count_response.count or 0

    print("QR EN LISTA:", len(qr_tokens))
    print("QR EN BD:", total_qr)

    return render_template(
        "admin_qrs.html",
        qr_tokens=qr_tokens,
        total_qr=total_qr
    )
    
@admin_bp.route("/admin/qrs/<qr_id>/download")
@login_required
def download_qr_token(qr_id):
    db = get_db()
    response = db.table('qr_tokens').select(
        'token, qr_imagen'
    ).eq('id', qr_id).limit(1).execute()

    if not response.data:
        return "QR no encontrado", 404

    qr = response.data[0]
    qr_image = qr.get('qr_imagen')
    if not qr_image:
        return "Este QR no tiene imagen disponible", 404

    try:
        image_bytes = base64.b64decode(qr_image)
    except Exception:
        return "La imagen del QR no se pudo decodificar", 500

    return send_file(
        io.BytesIO(image_bytes),
        mimetype='image/png',
        as_attachment=True,
        download_name=f"qr_{qr.get('token', qr_id)}.png"
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
    
    # Obtener datos relacionados manualmente
    registros = []
    for reg in registros_raw:
        emp_response = db.table('empleado').select('nombre').eq('id', reg['empleado_id']).execute()
        local_response = db.table('locales').select('nombre_local').eq('id', reg['locales_id']).execute()
        
        empleado_nombre = emp_response.data[0]['nombre'] if emp_response.data else 'Desconocido'
        local_nombre = local_response.data[0]['nombre_local'] if local_response.data else 'Desconocido'
        
        registros.append({
            'id': reg['id'],
            'empleado': empleado_nombre,
            'local': local_nombre,
            'fecha': reg['fecha_hora']
        })

    # Obtener QRs generados recientes
    response = db.table('qr_tokens').select('*').order('id', desc=True).limit(10).execute()
    qr_tokens = response.data

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
