"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.qrTokenRepository = exports.QrTokenRepository = void 0;
/**
 * QR Token Repository - Optimized with caching
 */
const BaseRepository_1 = require("./BaseRepository");
const cache_1 = require("../utils/cache");
const database_1 = require("../config/database");
class QrTokenRepository extends BaseRepository_1.BaseRepository {
    constructor() {
        super('qr_tokens', cache_1.qrTokensCache, 60000); // 1 minute cache
    }
    /**
     * Find by token with caching
     */
    async findByToken(token) {
        const cacheKey = `qr_token:${token}`;
        const cached = cache_1.qrTokensCache.get(cacheKey);
        if (cached)
            return cached;
        const { data, error } = await database_1.supabase
            .from('qr_tokens')
            .select('id, empleado_id, local_id, token')
            .eq('token', token)
            .single();
        if (error || !data)
            return null;
        cache_1.qrTokensCache.set(cacheKey, data, 60000);
        return data;
    }
    /**
     * Find by employee with caching
     */
    async findByEmpleado(empleadoId) {
        return this.findByField('empleado_id', empleadoId, 'id, empleado_id, local_id, token');
    }
    /**
     * Create QR token - optimized
     */
    async createToken(empleadoId, localId, token) {
        const { data, error } = await database_1.supabase
            .from('qr_tokens')
            .insert({
            empleado_id: empleadoId,
            local_id: localId,
            token
        })
            .select('id, empleado_id, local_id, token')
            .single();
        if (error || !data)
            return null;
        // Invalidate cache
        this.invalidateCache();
        return data;
    }
}
exports.QrTokenRepository = QrTokenRepository;
exports.qrTokenRepository = new QrTokenRepository();
//# sourceMappingURL=QrTokenRepository.js.map