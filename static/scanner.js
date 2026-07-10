let scanning = true;

function extractToken(decodedText) {
    try {
        const url = new URL(decodedText);
        const parts = url.pathname.split("/");
        return parts[parts.length - 1];
    } catch {
        return decodedText.trim();
    }
}

async function registrar(token) {
    const empleadoId = document.getElementById("empleadoId").value;
    const observaciones = document.getElementById("observaciones").value;
    const resultado = document.getElementById("resultado");

    const response = await fetch("/api/registrar", {
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
    } else {
        resultado.textContent = data.error || "Error al registrar";
    }

    setTimeout(() => { scanning = true; }, 2500);
}

function onScanSuccess(decodedText) {
    if (!scanning) return;
    scanning = false;
    registrar(extractToken(decodedText));
}

const html5QrCode = new Html5QrcodeScanner(
    "reader",
    { fps: 10, qrbox: { width: 250, height: 250 } },
    false
);

html5QrCode.render(onScanSuccess);
