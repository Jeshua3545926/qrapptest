/**
 * Optimized API Routes using repositories and caching
 */
import { Router, Request, Response } from 'express';
import { registroRepository } from '../repositories/RegistroRepository';
import { empleadoRepository } from '../repositories/EmpleadoRepository';
import { localRepository } from '../repositories/LocalRepository';
import { qrTokenRepository } from '../repositories/QrTokenRepository';
import { qrGeneradoRepository } from '../repositories/QrGeneradoRepository';
import { exportEmpleadosToExcel, importEmpleadosFromExcel } from '../services/exportService';
import { exportLocalesToExcel, importLocalesFromExcel } from '../services/exportService';
import { generalLimiter, strictLimiter } from '../middleware/rateLimit';
import { RegisterAttendanceRequest, RegisterAttendanceResponse } from '../types';
import { resolveLocalIdFromQrToken } from '../services/qrService';

const router = Router();

/**
 * POST /api/registrar_simple - Register attendance without session
 */
router.post('/registrar_simple', generalLimiter, async (req: Request, res: Response) => {
  try {
    const { empleado_id, qr_token, observaciones } = req.body as RegisterAttendanceRequest;
    
    if (!empleado_id || !qr_token) {
      return res.status(400).json({ error: 'empleado_id y qr_token son requeridos' });
    }

    const localId = await resolveLocalIdFromQrToken(qr_token);
    
    if (!localId) {
      return res.status(404).json({ error: 'No se pudo identificar el local desde el QR' });
    }

    const registro = await registroRepository.registerAttendance(
      empleado_id,
      localId,
      observaciones
    );

    if (!registro) {
      return res.status(500).json({ error: 'Error al registrar asistencia' });
    }

    res.json({
      success: true,
      mensaje: 'Asistencia registrada exitosamente',
      registro
    } as RegisterAttendanceResponse);
  } catch (error) {
    console.error('Error registering attendance:', error);
    res.status(500).json({ error: 'Error al registrar asistencia' });
  }
});

/**
 * POST /api/registrar - Register attendance with session
 */
router.post('/registrar', generalLimiter, async (req: Request, res: Response) => {
  try {
    const userId = (req as any).user?.user_id;
    const { qr_token, observaciones } = req.body;

    if (!userId) {
      return res.status(401).json({ error: 'No autorizado' });
    }

    if (!qr_token) {
      return res.status(400).json({ error: 'qr_token es requerido' });
    }

    const localId = await resolveLocalIdFromQrToken(qr_token);
    
    if (!localId) {
      return res.status(404).json({ error: 'No se pudo identificar el local desde el QR' });
    }

    const registro = await registroRepository.registerAttendance(
      userId,
      localId,
      observaciones
    );

    if (!registro) {
      return res.status(500).json({ error: 'Error al registrar asistencia' });
    }

    res.json({
      success: true,
      mensaje: 'Asistencia registrada exitosamente',
      registro
    } as RegisterAttendanceResponse);
  } catch (error) {
    console.error('Error registering attendance:', error);
    res.status(500).json({ error: 'Error al registrar asistencia' });
  }
});

/**
 * POST /api/registrar_qr_generado_simple - Register generated QR without session
 */
router.post('/registrar_qr_generado_simple', generalLimiter, async (req: Request, res: Response) => {
  try {
    const { empleado_id, qr_token, observaciones } = req.body as RegisterAttendanceRequest;
    
    if (!empleado_id || !qr_token) {
      return res.status(400).json({ error: 'empleado_id y qr_token son requeridos' });
    }

    const localId = await resolveLocalIdFromQrToken(qr_token);
    
    if (!localId) {
      return res.status(404).json({ error: 'No se pudo identificar el local desde el QR' });
    }

    const registro = await registroRepository.registerAttendance(
      empleado_id,
      localId,
      observaciones
    );

    if (!registro) {
      return res.status(500).json({ error: 'Error al registrar asistencia' });
    }

    res.json({
      success: true,
      mensaje: 'Asistencia registrada exitosamente',
      registro
    } as RegisterAttendanceResponse);
  } catch (error) {
    console.error('Error registering generated QR:', error);
    res.status(500).json({ error: 'Error al registrar asistencia' });
  }
});

/**
 * POST /api/registrar_qr_generado - Register generated QR with session
 */
router.post('/registrar_qr_generado', generalLimiter, async (req: Request, res: Response) => {
  try {
    const userId = (req as any).user?.user_id;
    const { qr_token, observaciones } = req.body;

    if (!userId) {
      return res.status(401).json({ error: 'No autorizado' });
    }

    if (!qr_token) {
      return res.status(400).json({ error: 'qr_token es requerido' });
    }

    const localId = await resolveLocalIdFromQrToken(qr_token);
    
    if (!localId) {
      return res.status(404).json({ error: 'No se pudo identificar el local desde el QR' });
    }

    const registro = await registroRepository.registerAttendance(
      userId,
      localId,
      observaciones
    );

    if (!registro) {
      return res.status(500).json({ error: 'Error al registrar asistencia' });
    }

    res.json({
      success: true,
      mensaje: 'Asistencia registrada exitosamente',
      registro
    } as RegisterAttendanceResponse);
  } catch (error) {
    console.error('Error registering generated QR:', error);
    res.status(500).json({ error: 'Error al registrar asistencia' });
  }
});

/**
 * GET /api/registros - Get attendance records (cached)
 */
router.get('/registros', generalLimiter, async (req: Request, res: Response) => {
  try {
    const registros = await registroRepository.getRecentWithNames(100);
    res.json(registros);
  } catch (error) {
    console.error('Error fetching registros:', error);
    res.status(500).json({ error: 'Error al obtener registros' });
  }
});

/**
 * DELETE /api/registros/:id - Delete attendance record
 */
router.delete('/registros/:id', strictLimiter, async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const success = await registroRepository.delete(id);
    
    if (!success) {
      return res.status(404).json({ error: 'Registro no encontrado' });
    }

    res.json({ success: true });
  } catch (error) {
    console.error('Error deleting registro:', error);
    res.status(500).json({ error: 'Error al eliminar registro' });
  }
});

/**
 * DELETE /api/qr_tokens/:id - Delete QR token
 */
router.delete('/qr_tokens/:id', strictLimiter, async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const success = await qrTokenRepository.delete(id);
    
    if (!success) {
      return res.status(404).json({ error: 'QR token no encontrado' });
    }

    res.json({ success: true });
  } catch (error) {
    console.error('Error deleting QR token:', error);
    res.status(500).json({ error: 'Error al eliminar QR token' });
  }
});

/**
 * GET /api/exportar-empleados - Export employees to Excel
 */
router.get('/exportar-empleados', generalLimiter, async (req: Request, res: Response) => {
  try {
    const excelBuffer = await exportEmpleadosToExcel();
    
    res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    res.setHeader('Content-Disposition', `attachment; filename=empleados_${Date.now()}.xlsx`);
    res.send(excelBuffer);
  } catch (error) {
    console.error('Error exporting empleados:', error);
    res.status(500).json({ error: 'Error al exportar empleados' });
  }
});

/**
 * POST /api/importar-empleados - Import employees from Excel
 */
router.post('/importar-empleados', strictLimiter, async (req: Request, res: Response) => {
  try {
    const file = (req as any).file;
    
    if (!file) {
      return res.status(400).json({ error: 'Archivo es requerido' });
    }

    await importEmpleadosFromExcel(file.buffer);
    res.json({ success: true });
  } catch (error) {
    console.error('Error importing empleados:', error);
    res.status(500).json({ error: 'Error al importar empleados' });
  }
});

/**
 * GET /api/locales - Get all locales (cached)
 */
router.get('/locales', async (req: Request, res: Response) => {
  try {
    const locales = await localRepository.getAllMinimal();
    res.json(locales);
  } catch (error) {
    console.error('Error fetching locales:', error);
    res.status(500).json({ error: 'Error al obtener locales' });
  }
});

/**
 * POST /api/locales - Create new local
 */
router.post('/locales', strictLimiter, async (req: Request, res: Response) => {
  try {
    const { nombre_local } = req.body;
    
    if (!nombre_local) {
      return res.status(400).json({ error: 'Nombre local es requerido' });
    }

    const local = await localRepository.create({ nombre_local });
    
    if (!local) {
      return res.status(500).json({ error: 'Error al crear local' });
    }

    res.json({ success: true, local });
  } catch (error) {
    console.error('Error creating local:', error);
    res.status(500).json({ error: 'Error al crear local' });
  }
});

/**
 * GET /api/exportar-locales - Export locales to Excel
 */
router.get('/exportar-locales', generalLimiter, async (req: Request, res: Response) => {
  try {
    const excelBuffer = await exportLocalesToExcel();
    
    res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    res.setHeader('Content-Disposition', `attachment; filename=locales_${Date.now()}.xlsx`);
    res.send(excelBuffer);
  } catch (error) {
    console.error('Error exporting locales:', error);
    res.status(500).json({ error: 'Error al exportar locales' });
  }
});

/**
 * POST /api/importar-locales - Import locales from Excel
 */
router.post('/importar-locales', strictLimiter, async (req: Request, res: Response) => {
  try {
    const file = (req as any).file;
    
    if (!file) {
      return res.status(400).json({ error: 'Archivo es requerido' });
    }

    await importLocalesFromExcel(file.buffer);
    res.json({ success: true });
  } catch (error) {
    console.error('Error importing locales:', error);
    res.status(500).json({ error: 'Error al importar locales' });
  }
});

export default router;
