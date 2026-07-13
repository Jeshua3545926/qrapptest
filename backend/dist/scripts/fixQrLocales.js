"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * Script para actualizar QRs viejos sin locales_id
 * Este script busca todos los QRs en qr_tokens que no tienen locales_id
 * y les asigna el local correspondiente creándolo si no existe
 */
const database_1 = require("../config/database");
async function fixQrLocales() {
    console.log('Iniciando actualización de QRs viejos...');
    try {
        // Get all QR tokens without local_id
        const { data: qrTokens, error: fetchError } = await database_1.supabase
            .from('qr_tokens')
            .select('id, nombre_local, local_id')
            .is('local_id', null);
        if (fetchError) {
            console.error('Error al obtener QR tokens:', fetchError);
            return;
        }
        if (!qrTokens || qrTokens.length === 0) {
            console.log('No se encontraron QRs sin locales_id');
            return;
        }
        console.log(`Se encontraron ${qrTokens.length} QRs sin locales_id`);
        let updated = 0;
        let errors = 0;
        for (const qr of qrTokens) {
            try {
                // Check if local exists
                const { data: existingLocal } = await database_1.supabase
                    .from('locales')
                    .select('id')
                    .eq('nombre_local', qr.nombre_local)
                    .single();
                let localId;
                if (existingLocal) {
                    localId = existingLocal.id;
                    console.log(`Local encontrado: ${qr.nombre_local} (ID: ${localId})`);
                }
                else {
                    // Create local
                    const { data: newLocal, error: createError } = await database_1.supabase
                        .from('locales')
                        .insert({ nombre_local: qr.nombre_local })
                        .select('id')
                        .single();
                    if (createError) {
                        console.error(`Error al crear local ${qr.nombre_local}:`, createError);
                        errors++;
                        continue;
                    }
                    localId = newLocal.id;
                    console.log(`Local creado: ${qr.nombre_local} (ID: ${localId})`);
                }
                // Update QR token with local_id
                const { error: updateError } = await database_1.supabase
                    .from('qr_tokens')
                    .update({ local_id: localId })
                    .eq('id', qr.id);
                if (updateError) {
                    console.error(`Error al actualizar QR ${qr.id}:`, updateError);
                    errors++;
                }
                else {
                    updated++;
                    console.log(`QR ${qr.id} actualizado con local_id: ${localId}`);
                }
            }
            catch (error) {
                console.error(`Error procesando QR ${qr.id}:`, error);
                errors++;
            }
        }
        console.log(`\nResumen:`);
        console.log(`- Total QRs procesados: ${qrTokens.length}`);
        console.log(`- QRs actualizados exitosamente: ${updated}`);
        console.log(`- Errores: ${errors}`);
    }
    catch (error) {
        console.error('Error general:', error);
    }
}
// Run the script
fixQrLocales()
    .then(() => {
    console.log('Script finalizado');
    process.exit(0);
})
    .catch((error) => {
    console.error('Error fatal:', error);
    process.exit(1);
});
//# sourceMappingURL=fixQrLocales.js.map