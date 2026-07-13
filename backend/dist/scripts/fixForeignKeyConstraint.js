"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * Script para modificar la restricción de clave foránea de registros_asistencia
 * Cambia de ON DELETE RESTRICT a ON DELETE SET NULL
 * Esto permite eliminar empleados sin borrar sus registros de asistencia
 */
const database_1 = require("../config/database");
async function fixForeignKeyConstraint() {
    console.log('Modificando restricción de clave foránea...');
    try {
        // Paso 1: Eliminar la restricción actual
        const { error: dropError } = await database_1.supabase.rpc('exec_sql', {
            sql: `
        ALTER TABLE registros_asistencia 
        DROP CONSTRAINT IF EXISTS registros_asistencia_empleado_id_fkey;
      `
        });
        if (dropError) {
            console.error('Error al eliminar restricción:', dropError);
            return;
        }
        console.log('Restricción eliminada exitosamente');
        // Paso 2: Crear la nueva restricción con ON DELETE SET NULL
        const { error: addError } = await database_1.supabase.rpc('exec_sql', {
            sql: `
        ALTER TABLE registros_asistencia 
        ADD CONSTRAINT registros_asistencia_empleado_id_fkey 
        FOREIGN KEY (empleado_id) 
        REFERENCES empleado(id) 
        ON DELETE SET NULL;
      `
        });
        if (addError) {
            console.error('Error al agregar nueva restricción:', addError);
            return;
        }
        console.log('Nueva restricción creada exitosamente con ON DELETE SET NULL');
        console.log('Ahora puedes eliminar empleados sin borrar sus registros de asistencia');
    }
    catch (error) {
        console.error('Error general:', error);
    }
}
// Ejecutar el script
fixForeignKeyConstraint()
    .then(() => {
    console.log('Script finalizado');
    process.exit(0);
})
    .catch((error) => {
    console.error('Error fatal:', error);
    process.exit(1);
});
//# sourceMappingURL=fixForeignKeyConstraint.js.map