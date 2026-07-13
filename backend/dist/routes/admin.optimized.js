"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * Optimized Admin Routes using repositories and caching
 */
const express_1 = require("express");
const RegistroRepository_1 = require("../repositories/RegistroRepository");
const EmpleadoRepository_1 = require("../repositories/EmpleadoRepository");
const LocalRepository_1 = require("../repositories/LocalRepository");
const AdminRepository_1 = require("../repositories/AdminRepository");
const QrGeneradoRepository_1 = require("../repositories/QrGeneradoRepository");
const qrService_1 = require("../services/qrService");
const qrService_2 = require("../services/qrService");
const exportService_1 = require("../services/exportService");
const rateLimit_1 = require("../middleware/rateLimit");
const database_1 = require("../config/database");
const router = (0, express_1.Router)();
/**
 * GET /admin - Dashboard with recent records (cached)
 */
router.get('/', rateLimit_1.generalLimiter, async (req, res) => {
    try {
        const registros = await RegistroRepository_1.registroRepository.getRecentWithNames(50);
        const qrTokens = await QrGeneradoRepository_1.qrGeneradoRepository.findAll({ limit: 50 });
        res.json({ registros, qr_tokens: qrTokens });
    }
    catch (error) {
        console.error('Error fetching admin data:', error);
        res.status(500).json({ error: 'Error al obtener datos' });
    }
});
/**
 * POST /admin/create-employee - Create new employee
 */
router.post('/create-employee', rateLimit_1.strictLimiter, async (req, res) => {
    try {
        const { nombre, nombre_empleado } = req.body;
        const nombreEmpleado = nombre || nombre_empleado;
        if (!nombreEmpleado) {
            return res.status(400).json({ error: 'Nombre es requerido' });
        }
        const empleado = await EmpleadoRepository_1.empleadoRepository.create({ nombre: nombreEmpleado });
        if (!empleado) {
            return res.status(500).json({ error: 'Error al crear empleado' });
        }
        res.json({ success: true, empleado });
    }
    catch (error) {
        console.error('Error creating employee:', error);
        res.status(500).json({ error: 'Error al crear empleado' });
    }
});
/**
 * GET /admin/settings - Get admin settings
 */
router.get('/settings', async (req, res) => {
    try {
        const adminId = req.user?.user_id;
        if (!adminId) {
            return res.status(401).json({ error: 'No autorizado' });
        }
        const admin = await AdminRepository_1.adminRepository.findById(adminId, 'id, nombre');
        res.json({ admin });
    }
    catch (error) {
        console.error('Error fetching settings:', error);
        res.status(500).json({ error: 'Error al obtener configuración' });
    }
});
/**
 * POST /admin/settings - Update admin settings
 */
router.post('/settings', rateLimit_1.strictLimiter, async (req, res) => {
    try {
        const adminId = req.user?.user_id;
        const { nombre, password } = req.body;
        if (!adminId) {
            return res.status(401).json({ error: 'No autorizado' });
        }
        const admin = await AdminRepository_1.adminRepository.updateCredentials(adminId, nombre, password);
        if (!admin) {
            return res.status(500).json({ error: 'Error al actualizar configuración' });
        }
        res.json({ success: true, admin });
    }
    catch (error) {
        console.error('Error updating settings:', error);
        res.status(500).json({ error: 'Error al actualizar configuración' });
    }
});
/**
 * GET /admin/descargar-registros - Download Excel
 */
router.get('/descargar-registros', rateLimit_1.generalLimiter, async (req, res) => {
    try {
        const excelBuffer = await (0, qrService_1.saveExcel)();
        res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
        res.setHeader('Content-Disposition', `attachment; filename=registros_${Date.now()}.xlsx`);
        res.send(excelBuffer);
    }
    catch (error) {
        console.error('Error downloading excel:', error);
        res.status(500).json({ error: 'Error al descargar registros' });
    }
});
/**
 * POST /admin/generar-qr - Generate custom QR
 */
router.post('/generar-qr', rateLimit_1.strictLimiter, async (req, res) => {
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
        const token = (0, qrService_2.generateQrToken)(nombre_local, nombre_empleado, fecha, hora);
        const frontendBase = process.env.FRONTEND_URL || 'http://localhost:5173';
        const qrUrl = `${frontendBase}/login?login_type=user&qr_token=${encodeURIComponent(token)}`;
        const qrGenerado = await QrGeneradoRepository_1.qrGeneradoRepository.createGenerated(nombre_local, nombre_empleado, fecha, hora, token);
        if (!qrGenerado) {
            return res.status(500).json({ error: 'Error al generar QR' });
        }
        res.json({ success: true, token, qr_url: qrUrl, local_id: localId });
    }
    catch (error) {
        console.error('Error generating QR:', error);
        res.status(500).json({ error: 'Error al generar QR' });
    }
});
/**
 * GET /admin/locales - Get all locales (cached)
 */
router.get('/locales', async (req, res) => {
    try {
        const locales = await LocalRepository_1.localRepository.getAllMinimal();
        res.json(locales);
    }
    catch (error) {
        console.error('Error fetching locales:', error);
        res.status(500).json({ error: 'Error al obtener locales' });
    }
});
/**
 * POST /admin/locales - Create new local
 */
router.post('/locales', rateLimit_1.strictLimiter, async (req, res) => {
    try {
        const { nombre_local } = req.body;
        if (!nombre_local) {
            return res.status(400).json({ error: 'Nombre local es requerido' });
        }
        const local = await LocalRepository_1.localRepository.create({ nombre_local });
        if (!local) {
            return res.status(500).json({ error: 'Error al crear local' });
        }
        res.json({ success: true, local });
    }
    catch (error) {
        console.error('Error creating local:', error);
        res.status(500).json({ error: 'Error al crear local' });
    }
});
/**
 * GET /admin/qr-tokens - Get all QR tokens from qr_tokens table
 */
router.get('/qr-tokens', async (req, res) => {
    try {
        let mappedGeneratedQrs = [];
        try {
            const { data: generatedQrs, error: generatedError } = await database_1.supabase
                .from('qrs_generados')
                .select('id, token, nombre_local, nombre_empleado, fecha, hora, creado_en, qr_imagen')
                .order('creado_en', { ascending: false });
            if (generatedError) {
                console.warn('Skipping generated QR tokens due to missing table or schema issue:', generatedError.message || generatedError);
            }
            else {
                mappedGeneratedQrs = (generatedQrs || []).map((qr) => ({
                    id: qr.id,
                    token: qr.token,
                    fecha_creacion: qr.creado_en,
                    created_at: qr.creado_en,
                    nombre_local: qr.nombre_local,
                    nombre_empleado: qr.nombre_empleado,
                    fecha: qr.fecha,
                    hora: qr.hora,
                    locales: { nombre_local: qr.nombre_local },
                    empleado: { nombre: qr.nombre_empleado },
                    qr_imagen: qr.qr_imagen
                }));
            }
        }
        catch (innerError) {
            console.warn('Skipped qrs_generados query due to error:', innerError?.message || innerError);
        }
        const { data: legacyQrTokens, error: legacyError } = await database_1.supabase
            .from('qr_tokens')
            .select(`
        id,
        token,
        fecha_creacion,
        empleado_id,
        local_id,
        empleado (nombre),
        locales (nombre_local)
      `)
            .order('fecha_creacion', { ascending: false });
        if (legacyError) {
            console.warn('Failed to query qr_tokens with fecha_creacion order:', legacyError.message || legacyError);
            throw legacyError;
        }
        const mappedLegacyQrTokens = (legacyQrTokens || []).map((qr) => ({
            ...qr,
            locales: qr.locales?.[0] ? qr.locales[0] : qr.locales,
            empleado: qr.empleado?.[0] ? qr.empleado[0] : qr.empleado
        }));
        res.json([...mappedGeneratedQrs, ...mappedLegacyQrTokens]);
    }
    catch (error) {
        console.error('Error fetching QR tokens:', error);
        res.status(500).json({ error: 'Error al obtener QR tokens' });
    }
});
/**
 * DELETE /admin/qr-tokens/:id - Delete a QR token
 */
router.delete('/qr-tokens/:id', async (req, res) => {
    try {
        const { id } = req.params;
        const { error } = await database_1.supabase
            .from('qr_tokens')
            .delete()
            .eq('id', id);
        if (error)
            throw error;
        res.json({ success: true });
    }
    catch (error) {
        console.error('Error deleting QR token:', error);
        res.status(500).json({ error: 'Error al eliminar QR token' });
    }
});
/**
 * GET /admin/export-empleados - Export empleados to Excel
 */
router.get('/export-empleados', rateLimit_1.generalLimiter, async (req, res) => {
    try {
        const excelBuffer = await (0, exportService_1.exportEmpleadosToExcel)();
        res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
        res.setHeader('Content-Disposition', `attachment; filename=empleados_${Date.now()}.xlsx`);
        res.send(excelBuffer);
    }
    catch (error) {
        console.error('Error exporting empleados:', error);
        res.status(500).json({ error: 'Error al exportar empleados' });
    }
});
/**
 * POST /admin/import-empleados - Import empleados from Excel
 */
router.post('/import-empleados', rateLimit_1.strictLimiter, async (req, res) => {
    try {
        const { empleados } = req.body;
        if (!empleados || !Array.isArray(empleados)) {
            return res.status(400).json({ error: 'Formato inválido' });
        }
        await (0, exportService_1.importEmpleadosFromExcel)(Buffer.from(JSON.stringify(empleados)));
        res.json({ success: true, count: empleados.length });
    }
    catch (error) {
        console.error('Error importing empleados:', error);
        res.status(500).json({ error: 'Error al importar empleados' });
    }
});
/**
 * PUT /empleados/:id - Update empleado
 */
router.put('/empleados/:id', async (req, res) => {
    try {
        const { id } = req.params;
        const { nombre } = req.body;
        if (!nombre) {
            return res.status(400).json({ error: 'Nombre es requerido' });
        }
        const empleado = await EmpleadoRepository_1.empleadoRepository.update(id, { nombre });
        if (!empleado) {
            return res.status(404).json({ error: 'Empleado no encontrado' });
        }
        res.json({ success: true, empleado });
    }
    catch (error) {
        console.error('Error updating empleado:', error);
        res.status(500).json({ error: 'Error al actualizar empleado' });
    }
});
/**
 * DELETE /empleados/:id - Delete empleado
 */
router.delete('/empleados/:id', async (req, res) => {
    try {
        const { id } = req.params;
        const success = await EmpleadoRepository_1.empleadoRepository.delete(id);
        if (!success) {
            return res.status(404).json({ error: 'Empleado no encontrado' });
        }
        res.json({ success: true });
    }
    catch (error) {
        console.error('Error deleting empleado:', error);
        res.status(500).json({ error: 'Error al eliminar empleado' });
    }
});
/**
 * GET /empleados - Get all empleados
 */
router.get('/empleados', async (req, res) => {
    try {
        const empleados = await EmpleadoRepository_1.empleadoRepository.findAll({}, 'id, nombre');
        res.json(empleados || []);
    }
    catch (error) {
        console.error('Error fetching empleados:', error);
        res.status(500).json({ error: 'Error al obtener empleados' });
    }
});
exports.default = router;
//# sourceMappingURL=admin.optimized.js.map