"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * Optimized Auth Routes using repositories and caching
 */
const express_1 = require("express");
const AdminRepository_1 = require("../repositories/AdminRepository");
const EmpleadoRepository_1 = require("../repositories/EmpleadoRepository");
const auth_1 = require("../middleware/auth");
const rateLimit_1 = require("../middleware/rateLimit");
const router = (0, express_1.Router)();
const FRONTEND_BASE = process.env.FRONTEND_URL || 'http://localhost:5173';
/**
 * POST /login - Optimized login with caching
 */
router.post('/login', rateLimit_1.loginLimiter, async (req, res) => {
    try {
        const { login_type, username, password, empleado_id } = req.body;
        if (login_type === 'admin') {
            // Use repository with caching
            const admin = await AdminRepository_1.adminRepository.findByUsername(username || '');
            if (!admin || admin.password !== password) {
                return res.status(401).json({ error: 'Usuario o contraseña incorrectos' });
            }
            const token = (0, auth_1.generateToken)('admin', admin.id, admin.nombre);
            res.cookie('jwt_token', token, {
                maxAge: 7 * 24 * 60 * 60 * 1000,
                httpOnly: false,
                secure: process.env.NODE_ENV === 'production',
                sameSite: 'strict'
            });
            return res.json({
                success: true,
                redirect: '/admin',
                token,
                user: { id: admin.id, nombre: admin.nombre, role: 'admin' }
            });
        }
        else if (login_type === 'user') {
            if (!empleado_id) {
                return res.status(400).json({ error: 'Se requiere empleado_id' });
            }
            // Use repository with caching
            const empleado = await EmpleadoRepository_1.empleadoRepository.findById(empleado_id, 'id, nombre');
            if (!empleado) {
                return res.status(401).json({ error: 'Empleado no encontrado' });
            }
            const token = (0, auth_1.generateToken)('user', empleado.id, empleado.nombre);
            res.cookie('jwt_token', token, {
                maxAge: 7 * 24 * 60 * 60 * 1000,
                httpOnly: false,
                secure: process.env.NODE_ENV === 'production',
                sameSite: 'strict'
            });
            return res.json({
                success: true,
                redirect: '/scanner',
                token,
                user: { id: empleado.id, nombre: empleado.nombre, role: 'user' }
            });
        }
        return res.status(400).json({ error: 'Tipo de login inválido' });
    }
    catch (error) {
        console.error('Login error:', error);
        return res.status(500).json({ error: 'Error en el servidor' });
    }
});
/**
 * POST /logout - Clear token
 */
router.post('/logout', (req, res) => {
    res.clearCookie('jwt_token');
    res.json({ success: true });
});
/**
 * GET /verify-token - Verify if token is valid
 */
router.get('/verify-token', (req, res) => {
    try {
        const token = req.headers.authorization?.replace('Bearer ', '');
        if (!token) {
            return res.json({ valid: false });
        }
        const { verifyToken } = require('../middleware/auth');
        const decoded = verifyToken(token);
        if (decoded) {
            res.json({ valid: true });
        }
        else {
            res.json({ valid: false });
        }
    }
    catch (error) {
        res.json({ valid: false });
    }
});
/**
 * GET /empleados - Get all employees (cached)
 */
router.get('/empleados', async (req, res) => {
    try {
        const empleados = await EmpleadoRepository_1.empleadoRepository.getAllMinimal();
        res.json(empleados);
    }
    catch (error) {
        console.error('Error fetching empleados:', error);
        res.status(500).json({ error: 'Error al obtener empleados' });
    }
});
router.get('/scan_qr_generado/:token', (req, res) => {
    const { token } = req.params;
    const redirectUrl = `${FRONTEND_BASE}/login?login_type=user&qr_token=${encodeURIComponent(token)}`;
    res.redirect(redirectUrl);
});
router.get('/scan/:token', (req, res) => {
    const { token } = req.params;
    const redirectUrl = `${FRONTEND_BASE}/login?login_type=user&qr_token=${encodeURIComponent(token)}`;
    res.redirect(redirectUrl);
});
exports.default = router;
//# sourceMappingURL=auth.optimized.js.map