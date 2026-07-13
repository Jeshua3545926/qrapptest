"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.registroRepository = exports.RegistroRepository = void 0;
/**
 * Registro Asistencia Repository - Optimized with caching
 */
const BaseRepository_1 = require("./BaseRepository");
const cache_1 = require("../utils/cache");
const database_1 = require("../config/database");
class RegistroRepository extends BaseRepository_1.BaseRepository {
    constructor() {
        super('registros_asistencia', cache_1.registrosCache, 30000); // 30 seconds cache
    }
    /**
     * Get recent records with employee and locale names (optimized join)
     */
    async getRecentWithNames(limit = 50) {
        const cacheKey = `registros:recent:${limit}`;
        // Check cache first
        const cached = cache_1.registrosCache.get(cacheKey);
        if (cached)
            return cached;
        // Optimized query with select only needed fields
        const { data, error } = await database_1.supabase
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
        if (error)
            return [];
        // Transform data for frontend
        const transformed = data.map((reg) => ({
            id: reg.id,
            empleado: reg.empleado?.nombre || 'Empleado eliminado',
            local: reg.locales?.nombre_local || 'Desconocido',
            fecha: reg.fecha_hora,
            observaciones: reg.observaciones
        }));
        // Cache the result
        cache_1.registrosCache.set(cacheKey, transformed, 30000);
        return transformed;
    }
    /**
     * Get records by employee with pagination
     */
    async getByEmpleado(empleadoId, page = 1, limit = 50) {
        const cacheKey = `registros:empleado:${empleadoId}:${page}:${limit}`;
        const cached = cache_1.registrosCache.get(cacheKey);
        if (cached)
            return cached;
        const { data, error } = await database_1.supabase
            .from('registros_asistencia')
            .select('id, empleado_id, locales_id, fecha_hora, observaciones')
            .eq('empleado_id', empleadoId)
            .order('fecha_hora', { ascending: false })
            .range((page - 1) * limit, page * limit - 1);
        if (error)
            return [];
        cache_1.registrosCache.set(cacheKey, data, 30000);
        return data;
    }
    /**
     * Get records by date range
     */
    async getByDateRange(startDate, endDate, page = 1, limit = 50) {
        const cacheKey = `registros:date:${startDate}:${endDate}:${page}:${limit}`;
        const cached = cache_1.registrosCache.get(cacheKey);
        if (cached)
            return cached;
        const { data, error } = await database_1.supabase
            .from('registros_asistencia')
            .select('id, empleado_id, locales_id, fecha_hora, observaciones')
            .gte('fecha_hora', startDate)
            .lte('fecha_hora', endDate)
            .order('fecha_hora', { ascending: false })
            .range((page - 1) * limit, page * limit - 1);
        if (error)
            return [];
        cache_1.registrosCache.set(cacheKey, data, 30000);
        return data;
    }
    /**
     * Register attendance - optimized single query
     */
    async registerAttendance(empleadoId, localId, observaciones) {
        const { data, error } = await database_1.supabase
            .from('registros_asistencia')
            .insert({
            empleado_id: empleadoId,
            locales_id: localId,
            fecha_hora: new Date().toISOString(),
            observaciones
        })
            .select('id, empleado_id, locales_id, fecha_hora, observaciones')
            .single();
        if (error)
            return null;
        // Invalidate cache
        this.invalidateCache();
        return data;
    }
}
exports.RegistroRepository = RegistroRepository;
exports.registroRepository = new RegistroRepository();
//# sourceMappingURL=RegistroRepository.js.map