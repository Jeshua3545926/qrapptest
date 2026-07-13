"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = require("express");
const database_1 = require("../config/database");
const qrService_1 = require("../services/qrService");
const router = (0, express_1.Router)();
router.get('/', async (req, res) => {
    try {
        // Get recent attendance records
        const { data: registros_raw, error: registrosError } = await database_1.supabase
            .from('registros_asistencia')
            .select('id, empleado_id, locales_id, fecha_hora, observaciones')
            .order('fecha_hora', { ascending: false })
            .limit(50);
        if (registrosError)
            throw registrosError;
        // Get employees and locales
        const { data: empleados } = await database_1.supabase
            .from('empleado')
            .select('id, nombre');
        const { data: locales } = await database_1.supabase
            .from('locales')
            .select('id, nombre_local');
        const empleados_dict = (empleados || []).reduce((acc, emp) => {
            acc[emp.id] = emp.nombre;
            return acc;
        }, {});
        const locales_dict = (locales || []).reduce((acc, loc) => {
            acc[loc.id] = loc.nombre_local;
            return acc;
        }, {});
        const registros = (registros_raw || []).map(reg => ({
            id: reg.id,
            empleado: reg.empleado_id ? (empleados_dict[reg.empleado_id] || 'Desconocido') : 'Empleado eliminado',
            local: locales_dict[reg.locales_id] || 'Desconocido',
            fecha: reg.fecha_hora,
            observaciones: reg.observaciones || ''
        }));
        // Get recent QR tokens
        const { data: qr_tokens } = await database_1.supabase
            .from('qr_tokens')
            .select('*')
            .order('id', { ascending: false })
            .limit(5);
        res.json({
            registros,
            qr_tokens: qr_tokens || []
        });
    }
    catch (error) {
        console.error('Admin dashboard error:', error);
        res.status(500).json({ error: 'Error al cargar datos' });
    }
});
router.post('/create-employee', async (req, res) => {
    try {
        const { nombre_empleado } = req.body;
        if (!nombre_empleado) {
            return res.status(400).json({ error: 'Debes ingresar el nombre del empleado' });
        }
        const { error } = await database_1.supabase
            .from('empleado')
            .insert({ nombre: nombre_empleado });
        if (error)
            throw error;
        res.json({ success: true, message: 'Empleado creado correctamente' });
    }
    catch (error) {
        console.error('Create employee error:', error);
        res.status(500).json({ error: 'Error al crear empleado' });
    }
});
router.get('/settings', async (req, res) => {
    try {
        const admin_id = req.user?.user_id;
        const { data: admin } = await database_1.supabase
            .from('admin')
            .select('*')
            .eq('id', admin_id)
            .single();
        res.json({
            admin_username: admin?.nombre || '',
            admin
        });
    }
    catch (error) {
        console.error('Settings error:', error);
        res.status(500).json({ error: 'Error al cargar configuración' });
    }
});
router.post('/settings', async (req, res) => {
    try {
        const admin_id = req.user?.user_id;
        if (!admin_id) {
            return res.status(401).json({ error: 'No autorizado' });
        }
        const { new_username, current_password, new_password, confirm_password } = req.body;
        // Get current admin
        const { data: admin } = await database_1.supabase
            .from('admin')
            .select('*')
            .eq('id', admin_id)
            .single();
        if (!admin) {
            return res.status(404).json({ error: 'Admin no encontrado' });
        }
        // Verify current password
        if (current_password && admin.password !== current_password) {
            return res.status(400).json({ error: 'La contraseña actual es incorrecta' });
        }
        if (new_password && new_password !== confirm_password) {
            return res.status(400).json({ error: 'Las nuevas contraseñas no coinciden' });
        }
        // Update admin
        const update_data = { nombre: new_username };
        if (new_password) {
            update_data.password = new_password;
        }
        const { error } = await database_1.supabase
            .from('admin')
            .update(update_data)
            .eq('id', admin_id);
        if (error)
            throw error;
        // Generate new token
        const { generateToken } = await Promise.resolve().then(() => __importStar(require('../middleware/auth')));
        const token = generateToken('admin', admin_id, new_username || admin.nombre);
        res.cookie('jwt_token', token, {
            maxAge: 7 * 24 * 60 * 60 * 1000,
            httpOnly: false
        });
        res.json({ success: true, message: 'Configuración actualizada' });
    }
    catch (error) {
        console.error('Update settings error:', error);
        res.status(500).json({ error: 'Error al actualizar configuración' });
    }
});
router.get('/descargar-registros', async (req, res) => {
    try {
        const excelBuffer = await (0, qrService_1.saveExcel)();
        res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
        res.setHeader('Content-Disposition', `attachment; filename=registros_${Date.now()}.xlsx`);
        res.send(excelBuffer);
    }
    catch (error) {
        console.error('Download records error:', error);
        res.status(500).json({ error: 'Error al generar Excel' });
    }
});
router.post('/generar-qr', async (req, res) => {
    try {
        const { nombre_local, nombre_empleado, fecha, hora } = req.body;
        if (!nombre_local || !nombre_empleado || !fecha || !hora) {
            return res.status(400).json({ error: 'Todos los campos son requeridos' });
        }
        // Create or get the local
        let localId;
        const { data: existingLocal } = await database_1.supabase
            .from('locales')
            .select('id')
            .eq('nombre_local', nombre_local)
            .single();
        if (existingLocal) {
            localId = existingLocal.id;
        }
        else {
            const { data: newLocal, error: createError } = await database_1.supabase
                .from('locales')
                .insert({ nombre_local })
                .select('id')
                .single();
            if (createError)
                throw createError;
            localId = newLocal.id;
        }
        const qr_token = (0, qrService_1.generateQrToken)(nombre_local, nombre_empleado, fecha, hora);
        const frontendBase = process.env.FRONTEND_URL || 'http://localhost:5173';
        const qr_url = `${frontendBase}/login?login_type=user&qr_token=${encodeURIComponent(qr_token)}`;
        const qr_image = (0, qrService_1.generateQrImage)(qr_url);
        // Save to database with local_id
        const { error } = await database_1.supabase
            .from('qr_tokens')
            .insert({
            nombre_local,
            nombre_empleado,
            fecha,
            hora,
            token: qr_token,
            qr_imagen: qr_image,
            local_id: localId
        });
        if (error)
            throw error;
        res.json({
            success: true,
            qr_token,
            qr_image,
            redirect: '/admin'
        });
    }
    catch (error) {
        console.error('Generate QR error:', error);
        res.status(500).json({ error: 'Error al generar QR' });
    }
});
router.get('/locales', async (req, res) => {
    try {
        const { data: locales, error } = await database_1.supabase
            .from('locales')
            .select('*')
            .order('nombre_local');
        if (error)
            throw error;
        res.json(locales || []);
    }
    catch (error) {
        console.error('Get locales error:', error);
        res.status(500).json({ error: 'Error al obtener locales' });
    }
});
router.post('/locales', async (req, res) => {
    try {
        const { nombre_local } = req.body;
        if (!nombre_local) {
            return res.status(400).json({ error: 'Nombre del local es requerido' });
        }
        const { error } = await database_1.supabase
            .from('locales')
            .insert({ nombre_local });
        if (error)
            throw error;
        res.json({ success: true, message: 'Local agregado correctamente' });
    }
    catch (error) {
        console.error('Create local error:', error);
        res.status(500).json({ error: 'Error al agregar local' });
    }
});
exports.default = router;
//# sourceMappingURL=admin.js.map