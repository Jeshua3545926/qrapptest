/**
 * QR Token Repository - Optimized with caching
 */
import { BaseRepository } from './BaseRepository';
import { QrToken } from '../types';
import { qrTokensCache } from '../utils/cache';
import { supabase } from '../config/database';

export class QrTokenRepository extends BaseRepository<QrToken> {
  constructor() {
    super('qr_tokens', qrTokensCache, 60000); // 1 minute cache
  }

  /**
   * Find by token with caching
   */
  async findByToken(token: string): Promise<QrToken | null> {
    const cacheKey = `qr_token:${token}`;
    
    const cached = qrTokensCache.get(cacheKey);
    if (cached) return cached;

    const { data, error } = await supabase
      .from('qr_tokens')
      .select('id, empleado_id, local_id, token')
      .eq('token', token)
      .single();

    if (error || !data) return null;

    qrTokensCache.set(cacheKey, data, 60000);
    return data as QrToken;
  }

  /**
   * Find by employee with caching
   */
  async findByEmpleado(empleadoId: string): Promise<QrToken[]> {
    return this.findByField('empleado_id', empleadoId, 'id, empleado_id, local_id, token');
  }

  /**
   * Create QR token - optimized
   */
  async createToken(empleadoId: string, localId: string, token: string): Promise<QrToken | null> {
    const { data, error } = await supabase
      .from('qr_tokens')
      .insert({
        empleado_id: empleadoId,
        local_id: localId,
        token
      })
      .select('id, empleado_id, local_id, token')
      .single();

    if (error || !data) return null;

    // Invalidate cache
    this.invalidateCache();
    
    return data as QrToken;
  }
}

export const qrTokenRepository = new QrTokenRepository();
