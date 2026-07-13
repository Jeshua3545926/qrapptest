-- Script para modificar la restricción de clave foránea de registros_asistencia
-- Cambia de ON DELETE RESTRICT a ON DELETE SET NULL
-- Esto permite eliminar empleados sin borrar sus registros de asistencia

-- Paso 1: Quitar restricción NOT NULL de empleado_id
ALTER TABLE registros_asistencia 
ALTER COLUMN empleado_id DROP NOT NULL;

-- Paso 2: Eliminar la restricción de clave foránea actual
ALTER TABLE registros_asistencia 
DROP CONSTRAINT IF EXISTS registros_asistencia_empleado_id_fkey;

-- Paso 3: Crear la nueva restricción con ON DELETE SET NULL
ALTER TABLE registros_asistencia 
ADD CONSTRAINT registros_asistencia_empleado_id_fkey 
FOREIGN KEY (empleado_id) 
REFERENCES empleado(id) 
ON DELETE SET NULL;

-- Verificar la restricción
SELECT 
    conname AS constraint_name,
    condeferrable AS deferrable,
    condeferred AS deferred,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'registros_asistencia'::regclass 
AND conname = 'registros_asistencia_empleado_id_fkey';
