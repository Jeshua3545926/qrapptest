import QRCode from 'qrcode';
import { supabase } from '../config/database';
import * as XLSX from 'xlsx';
import { localRepository } from '../repositories/LocalRepository';
import { qrTokenRepository } from '../repositories/QrTokenRepository';
import { qrGeneradoRepository } from '../repositories/QrGeneradoRepository';

export interface QrTokenPayload {
  type: 'local_attendance';
  local_name: string;
  nombre_empleado?: string;
  fecha?: string;
  hora?: string;
  created_at?: string;
}

export function generateQrToken(nombre_local: string, nombre_empleado: string, fecha: string, hora: string): string {
  const payload: QrTokenPayload = {
    type: 'local_attendance',
    local_name: nombre_local,
    nombre_empleado,
    fecha,
    hora,
    created_at: new Date().toISOString()
  };

  return Buffer.from(JSON.stringify(payload)).toString('base64url');
}

export function decodeQrPayload(token: string): QrTokenPayload | null {
  if (!token) return null;

  try {
    const parsed = JSON.parse(Buffer.from(token, 'base64url').toString('utf8')) as Partial<QrTokenPayload>;
    if (parsed?.type === 'local_attendance' && typeof parsed.local_name === 'string' && parsed.local_name.trim()) {
      return parsed as QrTokenPayload;
    }

    return null;
  } catch {
    return null;
  }
}

export async function resolveLocalIdFromQrToken(token: string): Promise<string | null> {
  const payload = decodeQrPayload(token);

  if (payload?.local_name) {
    let locales = await localRepository.findByNombre(payload.local_name);
    if (locales.length === 0) {
      // Create local if it doesn't exist
      const newLocal = await localRepository.create({ nombre_local: payload.local_name });
      if (newLocal) {
        return newLocal.id;
      }
    } else {
      return locales[0].id;
    }
  }

  const qrTokenData = await qrTokenRepository.findByToken(token);
  if (qrTokenData?.local_id) {
    return qrTokenData.local_id;
  }

  const qrGenerado = await qrGeneradoRepository.findByToken(token);
  if (qrGenerado?.nombre_local) {
    let locales = await localRepository.findByNombre(qrGenerado.nombre_local);
    if (locales.length === 0) {
      // Create local if it doesn't exist
      const newLocal = await localRepository.create({ nombre_local: qrGenerado.nombre_local });
      if (newLocal) {
        return newLocal.id;
      }
    } else {
      return locales[0].id;
    }
  }

  return null;
}

export async function generateQrImage(qr_url: string): Promise<string> {
  try {
    const qrDataUrl = await QRCode.toDataURL(qr_url);
    return qrDataUrl;
  } catch (error) {
    console.error('Error generating QR image:', error);
    throw new Error('Error al generar imagen QR');
  }
}

export async function saveExcel(): Promise<Buffer> {
  try {
    // Get attendance records
    const { data: registros_raw, error } = await supabase
      .from('registros_asistencia')
      .select('*')
      .order('fecha_hora', { ascending: false });

    if (error) throw error;

    // Get employees and locales
    const { data: empleados } = await supabase
      .from('empleado')
      .select('id, nombre');
    
    const { data: locales } = await supabase
      .from('locales')
      .select('id, nombre_local');

    const empleados_dict = (empleados || []).reduce((acc, emp) => {
      acc[emp.id] = emp.nombre;
      return acc;
    }, {} as Record<string, string>);

    const locales_dict = (locales || []).reduce((acc, loc) => {
      acc[loc.id] = loc.nombre_local;
      return acc;
    }, {} as Record<string, string>);

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
    
    return excelBuffer as Buffer;
  } catch (error) {
    console.error('Error saving Excel:', error);
    throw new Error('Error al generar Excel');
  }
}
