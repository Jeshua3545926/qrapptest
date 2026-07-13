"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * Optimized API Routes using repositories and caching
 */
const express_1 = require("express");
const RegistroRepository_1 = require("../repositories/RegistroRepository");
const LocalRepository_1 = require("../repositories/LocalRepository");
const QrTokenRepository_1 = require("../repositories/QrTokenRepository");
const exportService_1 = require("../services/exportService");
const exportService_2 = require("../services/exportService");
const rateLimit_1 = require("../middleware/rateLimit");
const qrService_1 = require("../services/qrService");
const router = (0, express_1.Router)();
/**
 * POST /api/registrar_simple - Register attendance without session
 */
router.post('/registrar_simple', rateLimit_1.generalLimiter, async (req, res) => {
    try {
        const { empleado_id, qr_token, observaciones } = req.body;
        if (!empleado_id || !qr_token) {
            return res.status(400).json({ error: 'empleado_id y qr_token son requeridos' });
        }
        const localId = await (0, qrService_1.resolveLocalIdFromQrToken)(qr_token);
        if (!localId) {
            return res.status(404).json({ error: 'No se pudo identificar el local desde el QR' });
        }
        const registro = await RegistroRepository_1.registroRepository.registerAttendance(empleado_id, localId, observaciones);
        if (!registro) {
            return res.status(500).json({ error: 'Error al registrar asistencia' });
        }
        res.json({
            success: true,
            mensaje: 'Asistencia registrada exitosamente',
            registro
        });
    }
    catch (error) {
        console.error('Error registering attendance:', error);
        res.status(500).json({ error: 'Error al registrar asistencia' });
    }
});
/**
 * POST /api/registrar - Register attendance with session
 */
router.post('/registrar', rateLimit_1.generalLimiter, async (req, res) => {
    try {
        const userId = req.user?.user_id;
        const { qr_token, observaciones } = req.body;
        if (!userId) {
            return res.status(401).json({ error: 'No autorizado' });
        }
        if (!qr_token) {
            return res.status(400).json({ error: 'qr_token es requerido' });
        }
        const localId = await (0, qrService_1.resolveLocalIdFromQrToken)(qr_token);
        if (!localId) {
            return res.status(404).json({ error: 'No se pudo identificar el local desde el QR' });
        }
        const registro = await RegistroRepository_1.registroRepository.registerAttendance(userId, localId, observaciones);
        if (!registro) {
            return res.status(500).json({ error: 'Error al registrar asistencia' });
        }
        res.json({
            success: true,
            mensaje: 'Asistencia registrada exitosamente',
            registro
        });
    }
    catch (error) {
        console.error('Error registering attendance:', error);
        res.status(500).json({ error: 'Error al registrar asistencia' });
    }
});
/**
 * POST /api/registrar_qr_generado_simple - Register generated QR without session
 */
router.post('/registrar_qr_generado_simple', rateLimit_1.generalLimiter, async (req, res) => {
    try {
        const { empleado_id, qr_token, observaciones } = req.body;
        if (!empleado_id || !qr_token) {
            return res.status(400).json({ error: 'empleado_id y qr_token son requeridos' });
        }
        const localId = await (0, qrService_1.resolveLocalIdFromQrToken)(qr_token);
        if (!localId) {
            return res.status(404).json({ error: 'No se pudo identificar el local desde el QR' });
        }
        const registro = await RegistroRepository_1.registroRepository.registerAttendance(empleado_id, localId, observaciones);
        if (!registro) {
            return res.status(500).json({ error: 'Error al registrar asistencia' });
        }
        res.json({
            success: true,
            mensaje: 'Asistencia registrada exitosamente',
            registro
        });
    }
    catch (error) {
        console.error('Error registering generated QR:', error);
        res.status(500).json({ error: 'Error al registrar asistencia' });
    }
});
/**
 * POST /api/registrar_qr_generado - Register generated QR with session
 */
router.post('/registrar_qr_generado', rateLimit_1.generalLimiter, async (req, res) => {
    try {
        const userId = req.user?.user_id;
        const { qr_token, observaciones } = req.body;
        if (!userId) {
            return res.status(401).json({ error: 'No autorizado' });
        }
        if (!qr_token) {
            return res.status(400).json({ error: 'qr_token es requerido' });
        }
        const localId = await (0, qrService_1.resolveLocalIdFromQrToken)(qr_token);
        if (!localId) {
            return res.status(404).json({ error: 'No se pudo identificar el local desde el QR' });
        }
        const registro = await RegistroRepository_1.registroRepository.registerAttendance(userId, localId, observaciones);
        if (!registro) {
            return res.status(500).json({ error: 'Error al registrar asistencia' });
        }
        res.json({
            success: true,
            mensaje: 'Asistencia registrada exitosamente',
            registro
        });
    }
    catch (error) {
        console.error('Error registering generated QR:', error);
        res.status(500).json({ error: 'Error al registrar asistencia' });
    }
});
/**
 * GET /api/registros - Get attendance records (cached)
 */
router.get('/registros', rateLimit_1.generalLimiter, async (req, res) => {
    try {
        const registros = await RegistroRepository_1.registroRepository.getRecentWithNames(100);
        res.json(registros);
    }
    catch (error) {
        console.error('Error fetching registros:', error);
        res.status(500).json({ error: 'Error al obtener registros' });
    }
});
/**
 * DELETE /api/registros/:id - Delete attendance record
 */
router.delete('/registros/:id', rateLimit_1.strictLimiter, async (req, res) => {
    try {
        const { id } = req.params;
        const success = await RegistroRepository_1.registroRepository.delete(id);
        if (!success) {
            return res.status(404).json({ error: 'Registro no encontrado' });
        }
        res.json({ success: true });
    }
    catch (error) {
        console.error('Error deleting registro:', error);
        res.status(500).json({ error: 'Error al eliminar registro' });
    }
});
/**
 * DELETE /api/qr_tokens/:id - Delete QR token
 */
router.delete('/qr_tokens/:id', rateLimit_1.strictLimiter, async (req, res) => {
    try {
        const { id } = req.params;
        const success = await QrTokenRepository_1.qrTokenRepository.delete(id);
        if (!success) {
            return res.status(404).json({ error: 'QR token no encontrado' });
        }
        res.json({ success: true });
    }
    catch (error) {
        console.error('Error deleting QR token:', error);
        res.status(500).json({ error: 'Error al eliminar QR token' });
    }
});
/**
 * GET /api/exportar-empleados - Export employees to Excel
 */
router.get('/exportar-empleados', rateLimit_1.generalLimiter, async (req, res) => {
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
 * POST /api/importar-empleados - Import employees from Excel
 */
router.post('/importar-empleados', rateLimit_1.strictLimiter, async (req, res) => {
    try {
        const file = req.file;
        if (!file) {
            return res.status(400).json({ error: 'Archivo es requerido' });
        }
        await (0, exportService_1.importEmpleadosFromExcel)(file.buffer);
        res.json({ success: true });
    }
    catch (error) {
        console.error('Error importing empleados:', error);
        res.status(500).json({ error: 'Error al importar empleados' });
    }
});
/**
 * GET /api/locales - Get all locales (cached)
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
 * POST /api/locales - Create new local
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
 * GET /api/exportar-locales - Export locales to Excel
 */
router.get('/exportar-locales', rateLimit_1.generalLimiter, async (req, res) => {
    try {
        const excelBuffer = await (0, exportService_2.exportLocalesToExcel)();
        res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
        res.setHeader('Content-Disposition', `attachment; filename=locales_${Date.now()}.xlsx`);
        res.send(excelBuffer);
    }
    catch (error) {
        console.error('Error exporting locales:', error);
        res.status(500).json({ error: 'Error al exportar locales' });
    }
});
/**
 * POST /api/importar-locales - Import locales from Excel
 */
router.post('/importar-locales', rateLimit_1.strictLimiter, async (req, res) => {
    try {
        const file = req.file;
        if (!file) {
            return res.status(400).json({ error: 'Archivo es requerido' });
        }
        await (0, exportService_2.importLocalesFromExcel)(file.buffer);
        res.json({ success: true });
    }
    catch (error) {
        console.error('Error importing locales:', error);
        res.status(500).json({ error: 'Error al importar locales' });
    }
});
exports.default = router;
//# sourceMappingURL=api.optimized.js.map