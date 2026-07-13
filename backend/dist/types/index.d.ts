/**
 * TypeScript type definitions for type safety and better developer experience
 */
export interface Empleado {
    id: string;
    nombre: string;
    created_at?: string;
}
export interface Local {
    id: string;
    nombre_local: string;
    created_at?: string;
}
export interface Admin {
    id: string;
    nombre: string;
    password: string;
    created_at?: string;
}
export interface QrToken {
    id: string;
    empleado_id: string;
    local_id: string;
    token: string;
    created_at?: string;
}
export interface RegistroAsistencia {
    id: string;
    empleado_id: string | null;
    locales_id: string;
    fecha_hora: string;
    observaciones?: string;
    created_at?: string;
}
export interface QrGenerado {
    id: string;
    nombre_local: string;
    nombre_empleado: string;
    fecha: string;
    hora: string;
    token: string;
    created_at?: string;
}
export interface LoginRequest {
    login_type: 'admin' | 'user';
    username?: string;
    password?: string;
    empleado_id?: string;
}
export interface LoginResponse {
    success: boolean;
    redirect: string;
    token: string;
    user?: {
        id: string;
        nombre: string;
        role: string;
    };
}
export interface RegisterAttendanceRequest {
    empleado_id: string;
    qr_token: string;
    local_id?: string;
    observaciones?: string;
}
export interface RegisterAttendanceResponse {
    success: boolean;
    mensaje: string;
    registro?: RegistroAsistencia;
}
export interface GenerateQRRequest {
    nombre_local: string;
    nombre_empleado: string;
    fecha: string;
    hora: string;
}
export interface GenerateQRResponse {
    success: boolean;
    token: string;
    qr_url: string;
}
export interface JWTPayload {
    role: string;
    user_id: string;
    username: string;
    iat: number;
    exp: number;
}
export interface PaginationParams {
    page?: number;
    limit?: number;
    orderBy?: string;
    ascending?: boolean;
}
export interface PaginatedResponse<T> {
    data: T[];
    total: number;
    page: number;
    limit: number;
    totalPages: number;
}
export interface APIError {
    error: string;
    code?: string;
    details?: any;
}
export interface ExcelRow {
    [key: string]: any;
}
//# sourceMappingURL=index.d.ts.map