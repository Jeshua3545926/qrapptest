import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.emp_export_service import export_empleados_to_excel, importar_empleados_from_excel
from services.locales_Service import exportar_locales_to_excel, importar_locales_from_excel
from flask import Blueprint, request, jsonify, session
from models.database import get_db
from utils.helpers import get_mexico_time
from utils.decorators import login_required

api_bp = Blueprint('api', __name__)

@api_bp.route("/api/registrar_simple", methods=["POST"])
def api_registrar_simple():
    data = request.get_json()
    empleado_id = data.get("empleado_id")
    qr_token = data.get("qr_token")
    observaciones = data.get("observaciones", "").strip()

    if not empleado_id or not qr_token:
        return jsonify({"ok": False, "error": "Falta empleado o QR"}), 400

    db = get_db()
    response = db.table('locales').select('*').eq('qr_token', qr_token).execute()
    locales = response.data

    if not locales:
        return jsonify({"ok": False, "error": "QR inválido"}), 404

    local = locales[0]

    response = db.table('empleado').select('*').eq('id', empleado_id).execute()
    empleados = response.data

    if not empleados:
        return jsonify({"ok": False, "error": "Empleado inválido"}), 404

    empleado = empleados[0]
    fecha = get_mexico_time()

    db.table('registros_asistencia').insert({
        'empleado_id': empleado_id,
        'locales_id': local['id'],
        'fecha_hora': fecha,
        'observaciones': observaciones
    }).execute()

    return jsonify({
        "ok": True,
        "mensaje": f"{empleado['nombre']} registró llegada/recolección en {local['nombre_local']}",
        "empleado": empleado["nombre"],
        "local": local["nombre_local"],
        "fecha": fecha,
    })

@api_bp.route("/api/registrar", methods=["POST"])
def api_registrar():
    data = request.get_json()
    empleado_id = data.get("empleado_id")
    qr_token = data.get("qr_token")

    if not empleado_id and session.get("role") == "user":
        empleado_id = session.get("user_id")

    if not empleado_id or not qr_token:
        return jsonify({"ok": False, "error": "Falta empleado o QR"}), 400

    db = get_db()
    response = db.table('locales').select('*').eq('qr_token', qr_token).execute()
    locales = response.data

    if not locales:
        return jsonify({"ok": False, "error": "QR inválido"}), 404

    local = locales[0]

    response = db.table('empleado').select('*').eq('id', empleado_id).execute()
    empleados = response.data

    if not empleados:
        return jsonify({"ok": False, "error": "Empleado inválido"}), 404

    empleado = empleados[0]
    fecha = get_mexico_time()

    db.table('registros_asistencia').insert({
        'empleado_id': empleado_id,
        'locales_id': local['id'],
        'fecha_hora': fecha,
        'observaciones': observaciones
    }).execute()

    return jsonify({
        "ok": True,
        "mensaje": f"{empleado['nombre']} registró llegada/recolección en {local['nombre_local']}",
        "empleado": empleado["nombre"],
        "local": local["nombre_local"],
        "fecha": fecha,
    })

@api_bp.route("/api/registrar_qr_generado_simple", methods=["POST"])
def api_registrar_qr_generado_simple():
    data = request.get_json()
    empleado_id = data.get("empleado_id")
    qr_token = data.get("qr_token")

    if not empleado_id or not qr_token:
        return jsonify({"ok": False, "error": "Falta empleado o QR"}), 400

    db = get_db()
    response = db.table('qr_tokens').select('*').eq('token', qr_token).execute()
    qrs = response.data

    if not qrs:
        return jsonify({"ok": False, "error": "QR inválido"}), 404

    qr_generado = qrs[0]

    response = db.table('empleado').select('*').eq('id', empleado_id).execute()
    empleados = response.data

    if not empleados:
        return jsonify({"ok": False, "error": "Empleado inválido"}), 404

    empleado = empleados[0]
    fecha = get_mexico_time()

    # Verificar si el local existe en la tabla locales
    response = db.table('locales').select('*').eq('nombre_local', qr_generado['nombre_local']).execute()
    locales = response.data

    if not locales:
        # Crear local
        new_local = db.table('locales').insert({
            'nombre_local': qr_generado['nombre_local'],
            'qr_token': qr_token
        }).execute()
        local_id = new_local.data[0]['id']
    else:
        local_id = locales[0]['id']

    db.table('registros_asistencia').insert({
        'empleado_id': empleado_id,
        'locales_id': local_id,
        'fecha_hora': fecha,
        'token_id': qr_generado['id']
    }).execute()

    return jsonify({
        "ok": True,
        "mensaje": f"{empleado['nombre']} registró QR personalizado: {qr_generado['nombre_local']} - {qr_generado['nombre_empleado']}",
        "empleado": empleado["nombre"],
        "local": qr_generado["nombre_local"],
        "empleado_qr": qr_generado["nombre_empleado"],
        "fecha_qr": qr_generado["fecha"],
        "hora_qr": qr_generado["hora"],
        "fecha": fecha,
    })

@api_bp.route("/api/registrar_qr_generado", methods=["POST"])
def api_registrar_qr_generado():
    data = request.get_json()
    empleado_id = data.get("empleado_id")
    qr_token = data.get("qr_token")

    if not empleado_id and session.get("role") == "user":
        empleado_id = session.get("user_id")

    if not empleado_id or not qr_token:
        return jsonify({"ok": False, "error": "Falta empleado o QR"}), 400

    db = get_db()
    response = db.table('qr_tokens').select('*').eq('token', qr_token).execute()
    qrs = response.data

    if not qrs:
        return jsonify({"ok": False, "error": "QR inválido"}), 404

    qr_generado = qrs[0]

    response = db.table('empleado').select('*').eq('id', empleado_id).execute()
    empleados = response.data

    if not empleados:
        return jsonify({"ok": False, "error": "Empleado inválido"}), 404

    empleado = empleados[0]
    fecha = get_mexico_time()

    # Verificar si el local existe en la tabla locales
    response = db.table('locales').select('*').eq('nombre_local', qr_generado['nombre_local']).execute()
    locales = response.data

    if not locales:
        # Crear local
        new_local = db.table('locales').insert({
            'nombre_local': qr_generado['nombre_local'],
            'qr_token': qr_token
        }).execute()
        local_id = new_local.data[0]['id']
    else:
        local_id = locales[0]['id']

    db.table('registros_asistencia').insert({
        'empleado_id': empleado_id,
        'locales_id': local_id,
        'fecha_hora': fecha,
        'token_id': qr_generado['id']
    }).execute()

    return jsonify({
        "ok": True,
        "mensaje": f"{empleado['nombre']} registró QR personalizado: {qr_generado['nombre_local']} - {qr_generado['nombre_empleado']}",
        "empleado": empleado["nombre"],
        "local": qr_generado["nombre_local"],
        "empleado_qr": qr_generado["nombre_empleado"],
        "fecha_qr": qr_generado["fecha"],
        "hora_qr": qr_generado["hora"],
        "fecha": fecha,
    })

@api_bp.route("/api/registros")
def api_registros():
    import time
    db = get_db()
    
    # Obtener registros con reintentos
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = db.table('registros_asistencia').select('*').order('fecha_hora', desc=True).limit(20).execute()
            registros_raw = response.data
            break
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)
                continue
            else:
                return jsonify({"error": f"Error de conexión con Supabase: {str(e)}"}), 500
    
    # Obtener datos relacionados manualmente
    registros = []
    for reg in registros_raw:
        # Obtener empleado con reintentos
        empleado_nombre = 'Desconocido'
        for attempt in range(max_retries):
            try:
                emp_response = db.table('empleado').select('nombre').eq('id', reg['empleado_id']).execute()
                if emp_response.data:
                    empleado_nombre = emp_response.data[0]['nombre']
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                else:
                    empleado_nombre = 'Error'
        
        # Obtener local con reintentos
        local_nombre = 'Desconocido'
        for attempt in range(max_retries):
            try:
                local_response = db.table('locales').select('nombre_local').eq('id', reg['locales_id']).execute()
                if local_response.data:
                    local_nombre = local_response.data[0]['nombre_local']
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                else:
                    local_nombre = 'Error'
        
        registros.append({
            'id': reg['id'],
            'empleado': empleado_nombre,
            'local': local_nombre,
            'fecha': reg['fecha_hora'],
            'observaciones': reg.get('observaciones', '')
        })

    return jsonify(registros)

@api_bp.route("/api/registros/<registro_id>", methods=["DELETE"])
@login_required
def delete_registro(registro_id):
    db = get_db()
    db.table('registros_asistencia').delete().eq('id', registro_id).execute()
    return jsonify({"ok": True, "message": "Registro eliminado"})

@api_bp.route("/api/qr_tokens/<qr_id>", methods=["DELETE"])
@login_required
def hide_qr_generado(qr_id):
    db = get_db()
    db.table('qr_tokens').delete().eq('id', qr_id).execute()
    return jsonify({"ok": True, "message": "QR eliminado"})


@api_bp.route("/api/exportar-empleados")
def exportar_empleados():
    db = get_db()
    excel_bytes = export_empleados_to_excel(db)
    return excel_bytes

@api_bp.route("/api/importar-empleados", methods=["POST"])
def importar_empleados_route():
    if 'file' not in request.files:
        return jsonify({"ok": False, "message": "No se envió ningún archivo"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"ok": False, "message": "No se seleccionó ningún archivo"}), 400
    
    db = get_db()
    excel_bytes = file.read()
    importar_empleados_from_excel(db, excel_bytes)
    return jsonify({"ok": True, "message": "Empleados importados"})


@api_bp.route("/api/locales", methods=["GET", "POST"])
def locales():
    db = get_db()
    
    if request.method == "POST":
        data = request.get_json()
        nombre_local = data.get('nombre_local', '').strip()
        
        if not nombre_local:
            return jsonify({"ok": False, "message": "Nombre del local es requerido"}), 400
        
        try:
            db.table('locales').insert({'nombre_local': nombre_local}).execute()
            return jsonify({"ok": True, "message": "Local agregado correctamente"})
        except Exception as e:
            return jsonify({"ok": False, "message": f"Error al agregar local: {str(e)}"}), 500
    
    # GET request
    response = db.table('locales').select('*').execute()
    return jsonify(response.data)

@api_bp.route("/api/exportar-locales")
def exportar_locales():
    db = get_db()
    excel_bytes = exportar_locales_to_excel(db)
    return excel_bytes

@api_bp.route("/api/importar-locales", methods=["POST"])
def importar_locales():
    if 'file' not in request.files:
        return jsonify({"ok": False, "message": "No se envió ningún archivo"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"ok": False, "message": "No se seleccionó ningún archivo"}), 400
    
    db = get_db()
    excel_bytes = file.read()
    importar_locales_from_excel(db, excel_bytes)
    return jsonify({"ok": True, "message": "Locales importados"})