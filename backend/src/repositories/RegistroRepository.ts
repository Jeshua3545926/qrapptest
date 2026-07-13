/**
 * Registro Asistencia Repository - Optimized with caching
 */
import { BaseRepository } from './BaseRepository';
import { RegistroAsistencia } from '../types';
import { registrosCache } from '../utils/cache';
import { supabase } from '../config/database';

export class RegistroRepository extends BaseRepository<RegistroAsistencia> {
  constructor() {
    super('registros_asistencia', registrosCache, 30000); // 30 seconds cache
  }

  /**
   * Get recent records with employee and locale names (optimized join)
   */
  async getRecentWithNames(limit: number = 50): Promise<any[]> {
    const cacheKey = `registros:recent:${limit}`;
    
    // Check cache first
    const cached = registrosCache.get(cacheKey);
    if (cached) return cached;

    // Optimized query with select only needed fields
    const { data, error } = await supabase
      .from('registros_asistencia')
      .select(`
        id,
        empleado_id,
        locales_id,
        fecha_hora,
        observaciones,
        empleado(id, nombre),
        locales!inner(id, nombre_local)
      `)
      .order('fecha_hora', { ascending: false })
      .limit(limit);

    if (error) return [];

    // Transform data for frontend
    const transformed = data.map((reg: any) => ({
      id: reg.id,
      empleado: reg.empleado?.nombre || 'Empleado eliminado',
      local: reg.locales?.nombre_local || 'Desconocido',
      fecha: reg.fecha_hora,
      observaciones: reg.observaciones
    }));

    // Cache the result
    registrosCache.set(cacheKey, transformed, 30000);
    
    return transformed;
  }

  /**
   * Get records by employee with pagination
   */
  async getByEmpleado(
    empleadoId: string,
    page: number = 1,
    limit: number = 50
  ): Promise<RegistroAsistencia[]> {
    const cacheKey = `registros:empleado:${empleadoId}:${page}:${limit}`;
    
    const cached = registrosCache.get(cacheKey);
    if (cached) return cached;

    const { data, error } = await supabase
      .from('registros_asistencia')
      .select('id, empleado_id, locales_id, fecha_hora, observaciones')
      .eq('empleado_id', empleadoId)
      .order('fecha_hora', { ascending: false })
      .range((page - 1) * limit, page * limit - 1);

    if (error) return [];

    registrosCache.set(cacheKey, data, 30000);
    return data as RegistroAsistencia[];
  }

  /**
   * Get records by date range
   */
  async getByDateRange(
    startDate: string,
    endDate: string,
    page: number = 1,
    limit: number = 50
  ): Promise<RegistroAsistencia[]> {
    const cacheKey = `registros:date:${startDate}:${endDate}:${page}:${limit}`;
    
    const cached = registrosCache.get(cacheKey);
    if (cached) return cached;

    const { data, error } = await supabase
      .from('registros_asistencia')
      .select('id, empleado_id, locales_id, fecha_hora, observaciones')
      .gte('fecha_hora', startDate)
      .lte('fecha_hora', endDate)
      .order('fecha_hora', { ascending: false })
      .range((page - 1) * limit, page * limit - 1);

    if (error) return [];

    registrosCache.set(cacheKey, data, 30000);
    return data as RegistroAsistencia[];
  }

  /**
   * Register attendance - optimized single query
   */
  async registerAttendance(
    empleadoId: string,
    localId: string,
    observaciones?: string
  ): Promise<RegistroAsistencia | null> {
    const { data, error } = await supabase
      .from('registros_asistencia')
      .insert({
        empleado_id: empleadoId,
        locales_id: localId,
        fecha_hora: new Date().toISOString(),
        observaciones
      })
      .select('id, empleado_id, locales_id, fecha_hora, observaciones')
      .single();

    if (error) return null;

    // Invalidate cache
    this.invalidateCache();
    
    return data as RegistroAsistencia;
  }
}

export const registroRepository = new RegistroRepository();
