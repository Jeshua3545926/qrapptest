import { Router, Request, Response } from 'express';
import { supabase } from '../config/database';
import { AuthRequest } from '../middleware/auth';
import { generateQrToken, generateQrImage, saveExcel } from '../services/qrService';

const router = Router();

router.get('/', async (req: AuthRequest, res: Response) => {
  try {
    // Get recent attendance records
    const { data: registros_raw, error: registrosError } = await supabase
      .from('registros_asistencia')
      .select('id, empleado_id, locales_id, fecha_hora, observaciones')
      .order('fecha_hora', { ascending: false })
      .limit(50);

    if (registrosError) throw registrosError;

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

    const registros = (registros_raw || []).map(reg => ({
      id: reg.id,
      empleado: reg.empleado_id ? (empleados_dict[reg.empleado_id] || 'Desconocido') : 'Empleado eliminado',
      local: locales_dict[reg.locales_id] || 'Desconocido',
      fecha: reg.fecha_hora,
      observaciones: reg.observaciones || ''
    }));

    // Get recent QR tokens
    const { data: qr_tokens } = await supabase
      .from('qr_tokens')
      .select('*')
      .order('id', { ascending: false })
      .limit(5);

    res.json({
      registros,
      qr_tokens: qr_tokens || []
    });
  } catch (error) {
    console.error('Admin dashboard error:', error);
    res.status(500).json({ error: 'Error al cargar datos' });
  }
});

router.post('/create-employee', async (req: AuthRequest, res: Response) => {
  try {
    const { nombre_empleado } = req.body;
    
    if (!nombre_empleado) {
      return res.status(400).json({ error: 'Debes ingresar el nombre del empleado' });
    }

    const { error } = await supabase
      .from('empleado')
      .insert({ nombre: nombre_empleado });

    if (error) throw error;
    res.json({ success: true, message: 'Empleado creado correctamente' });
  } catch (error) {
    console.error('Create employee error:', error);
    res.status(500).json({ error: 'Error al crear empleado' });
  }
});

router.get('/settings', async (req: AuthRequest, res: Response) => {
  try {
    const admin_id = req.user?.user_id;
    
    const { data: admin } = await supabase
      .from('admin')
      .select('*')
      .eq('id', admin_id)
      .single();

    res.json({ 
      admin_username: admin?.nombre || '',
      admin 
    });
  } catch (error) {
    console.error('Settings error:', error);
    res.status(500).json({ error: 'Error al cargar configuración' });
  }
});

router.post('/settings', async (req: AuthRequest, res: Response) => {
  try {
    const admin_id = req.user?.user_id;
    if (!admin_id) {
      return res.status(401).json({ error: 'No autorizado' });
    }

    const { new_username, current_password, new_password, confirm_password } = req.body;

    // Get current admin
    const { data: admin } = await supabase
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
    const update_data: any = { nombre: new_username };
    if (new_password) {
      update_data.password = new_password;
    }

    const { error } = await supabase
      .from('admin')
      .update(update_data)
      .eq('id', admin_id);

    if (error) throw error;

    // Generate new token
    const { generateToken } = await import('../middleware/auth');
    const token = generateToken('admin', admin_id, new_username || admin.nombre);
    
    res.cookie('jwt_token', token, {
      maxAge: 7 * 24 * 60 * 60 * 1000,
      httpOnly: false
    });

    res.json({ success: true, message: 'Configuración actualizada' });
  } catch (error) {
    console.error('Update settings error:', error);
    res.status(500).json({ error: 'Error al actualizar configuración' });
  }
});

router.get('/descargar-registros', async (req: AuthRequest, res: Response) => {
  try {
    const excelBuffer = await saveExcel();
    
    res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    res.setHeader('Content-Disposition', `attachment; filename=registros_${Date.now()}.xlsx`);
    res.send(excelBuffer);
  } catch (error) {
    console.error('Download records error:', error);
    res.status(500).json({ error: 'Error al generar Excel' });
  }
});

router.post('/generar-qr', async (req: AuthRequest, res: Response) => {
  try {
    const { nombre_local, nombre_empleado, fecha, hora } = req.body;

    if (!nombre_local || !nombre_empleado || !fecha || !hora) {
      return res.status(400).json({ error: 'Todos los campos son requeridos' });
    }

    // Create or get the local
    let localId: string;
    const { data: existingLocal } = await supabase
      .from('locales')
      .select('id')
      .eq('nombre_local', nombre_local)
      .single();

    if (existingLocal) {
      localId = existingLocal.id;
    } else {
      const { data: newLocal, error: createError } = await supabase
        .from('locales')
        .insert({ nombre_local })
        .select('id')
        .single();

      if (createError) throw createError;
      localId = newLocal.id;
    }

    const qr_token = generateQrToken(nombre_local, nombre_empleado, fecha, hora);
    const frontendBase = process.env.FRONTEND_URL || 'http://localhost:5173';
    const qr_url = `${frontendBase}/login?login_type=user&qr_token=${encodeURIComponent(qr_token)}`;
    const qr_image = generateQrImage(qr_url);

    // Save to database with local_id
    const { error } = await supabase
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

    if (error) throw error;

    res.json({ 
      success: true, 
      qr_token, 
      qr_image,
      redirect: '/admin'
    });
  } catch (error) {
    console.error('Generate QR error:', error);
    res.status(500).json({ error: 'Error al generar QR' });
  }
});

router.get('/locales', async (req: AuthRequest, res: Response) => {
  try {
    const { data: locales, error } = await supabase
      .from('locales')
      .select('*')
      .order('nombre_local');

    if (error) throw error;
    res.json(locales || []);
  } catch (error) {
    console.error('Get locales error:', error);
    res.status(500).json({ error: 'Error al obtener locales' });
  }
});

router.post('/locales', async (req: AuthRequest, res: Response) => {
  try {
    const { nombre_local } = req.body;
    
    if (!nombre_local) {
      return res.status(400).json({ error: 'Nombre del local es requerido' });
    }

    const { error } = await supabase
      .from('locales')
      .insert({ nombre_local });

    if (error) throw error;
    res.json({ success: true, message: 'Local agregado correctamente' });
  } catch (error) {
    console.error('Create local error:', error);
    res.status(500).json({ error: 'Error al agregar local' });
  }
});

export default router;
