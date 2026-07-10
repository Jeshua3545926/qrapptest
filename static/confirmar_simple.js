document.getElementById("btnRegistrar").addEventListener("click", async function () {
    const empleadoId = document.getElementById("empleadoId").value;
    const token = this.dataset.token;
    const observaciones = document.getElementById("observaciones").value;
    const resultado = document.getElementById("resultado");

    if (!empleadoId) {
        resultado.classList.remove("hidden");
        resultado.textContent = "Por favor selecciona tu nombre";
        return;
    }

    const response = await fetch("/api/registrar_simple", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ empleado_id: empleadoId, qr_token: token, observaciones: observaciones })
    });

    const data = await response.json();
    resultado.classList.remove("hidden");

    if (data.ok) {
        const estadoCorreo = data.correo_enviado
            ? "enviado"
            : (data.correo_mensaje || "no enviado");
        resultado.textContent = `${data.mensaje} - ${data.fecha}. Correo: ${estadoCorreo}`;
        resultado.style.color = "var(--success)";
    } else {
        resultado.textContent = data.error || "Error al registrar";
        resultado.style.color = "var(--danger)";
    }
});
