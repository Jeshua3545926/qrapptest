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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateQrToken = generateQrToken;
exports.decodeQrPayload = decodeQrPayload;
exports.resolveLocalIdFromQrToken = resolveLocalIdFromQrToken;
exports.generateQrImage = generateQrImage;
exports.saveExcel = saveExcel;
const qrcode_1 = __importDefault(require("qrcode"));
const database_1 = require("../config/database");
const XLSX = __importStar(require("xlsx"));
const LocalRepository_1 = require("../repositories/LocalRepository");
const QrTokenRepository_1 = require("../repositories/QrTokenRepository");
const QrGeneradoRepository_1 = require("../repositories/QrGeneradoRepository");
function generateQrToken(nombre_local, nombre_empleado, fecha, hora) {
    const payload = {
        type: 'local_attendance',
        local_name: nombre_local,
        nombre_empleado,
        fecha,
        hora,
        created_at: new Date().toISOString()
    };
    return Buffer.from(JSON.stringify(payload)).toString('base64url');
}
function decodeQrPayload(token) {
    if (!token)
        return null;
    try {
        const parsed = JSON.parse(Buffer.from(token, 'base64url').toString('utf8'));
        if (parsed?.type === 'local_attendance' && typeof parsed.local_name === 'string' && parsed.local_name.trim()) {
            return parsed;
        }
        return null;
    }
    catch {
        return null;
    }
}
async function resolveLocalIdFromQrToken(token) {
    const payload = decodeQrPayload(token);
    if (payload?.local_name) {
        let locales = await LocalRepository_1.localRepository.findByNombre(payload.local_name);
        if (locales.length === 0) {
            // Create local if it doesn't exist
            const newLocal = await LocalRepository_1.localRepository.create({ nombre_local: payload.local_name });
            if (newLocal) {
                return newLocal.id;
            }
        }
        else {
            return locales[0].id;
        }
    }
    const qrTokenData = await QrTokenRepository_1.qrTokenRepository.findByToken(token);
    if (qrTokenData?.local_id) {
        return qrTokenData.local_id;
    }
    const qrGenerado = await QrGeneradoRepository_1.qrGeneradoRepository.findByToken(token);
    if (qrGenerado?.nombre_local) {
        let locales = await LocalRepository_1.localRepository.findByNombre(qrGenerado.nombre_local);
        if (locales.length === 0) {
            // Create local if it doesn't exist
            const newLocal = await LocalRepository_1.localRepository.create({ nombre_local: qrGenerado.nombre_local });
            if (newLocal) {
                return newLocal.id;
            }
        }
        else {
            return locales[0].id;
        }
    }
    return null;
}
async function generateQrImage(qr_url) {
    try {
        const qrDataUrl = await qrcode_1.default.toDataURL(qr_url);
        return qrDataUrl;
    }
    catch (error) {
        console.error('Error generating QR image:', error);
        throw new Error('Error al generar imagen QR');
    }
}
async function saveExcel() {
    try {
        // Get attendance records
        const { data: registros_raw, error } = await database_1.supabase
            .from('registros_asistencia')
            .select('*')
            .order('fecha_hora', { ascending: false });
        if (error)
            throw error;
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
        // Format records
        const registros = (registros_raw || []).map(reg => ({
            ID: reg.id,
            Empleado: empleados_dict[reg.empleado_id] || 'Desconocido',
            Local: locales_dict[reg.locales_id] || 'Desconocido',
            Fecha: reg.fecha_hora,
            Observaciones: reg.observaciones || ''
        }));
        // Create Excel workbook
        const worksheet = XLSX.utils.json_to_sheet(registros);
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, 'Registros');
        // Write to buffer
        const excelBuffer = XLSX.write(workbook, { type: 'buffer', bookType: 'xlsx' });
        return excelBuffer;
    }
    catch (error) {
        console.error('Error saving Excel:', error);
        throw new Error('Error al generar Excel');
    }
}
//# sourceMappingURL=qrService.js.map