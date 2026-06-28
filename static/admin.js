async function actualizarRegistros() {
    try {
        const response = await fetch("/api/registros");

        if (!response.ok) {
            console.error("Error cargando registros:", response.status);
            return;
        }

        const registros = await response.json();
        const tbody = document.querySelector("#tablaRegistros tbody");
        tbody.innerHTML = "";

        registros.forEach(r => {
            const tr = document.createElement("tr");
            tr.setAttribute("data-id", r.id);
            tr.innerHTML = `
                <td>${r.id}</td>
                <td>${r.empleado}</td>
                <td>${r.local}</td>
                <td>${r.fecha}</td>
                <td>
                    <button class="delete-btn" onclick="deleteRegistro('${r.id}')" title="Eliminar registro">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M3 6h18"></path>
                            <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                            <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                        </svg>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error("Error actualizando registros:", error);
    }
}

async function deleteRegistro(registroId) {
    if (!confirm("¿Estás seguro de que deseas eliminar este registro?")) {
        return;
    }

    const token = document.cookie.split('; ').find(row => row.startsWith('jwt_token='));
    const headers = {};
    if (token) {
        headers['Authorization'] = `Bearer ${token.split('=')[1]}`;
    }

    const response = await fetch(`/api/registros/${registroId}`, {
        method: "DELETE",
        headers: headers
    });

    if (response.ok) {
        const row = document.querySelector(`tr[data-id="${registroId}"]`);
        if (row) { 
            row.remove();
        }
    } else {
        alert("Error al eliminar el registro");
    }
}

async function hideQR(qrId) {
    if (!confirm("¿Estás seguro de que deseas ocultar este QR del dashboard? El QR seguirá existiendo en la base de datos.")) {
        return;
    }

    const token = document.cookie.split('; ').find(row => row.startsWith('jwt_token='));
    const headers = {};
    if (token) {
        const tokenValue = token.split('=')[1];
        headers['Authorization'] = `Bearer ${tokenValue}`;
    }

    const response = await fetch(`/api/qr_tokens/${qrId}`, {
        method: "DELETE",
        headers: headers
    });

    if (response.ok) {
        const card = document.querySelector(`.qr-card[data-qr-id="${qrId}"]`);
        if (card) {
            card.remove();
        }
    } else {
        alert("Error al ocultar el QR");
    }
}

async function importarEmpleados(){
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.xlsx,.xls';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        const formData = new FormData();
        formData.append('file', file);
        
        const token = document.cookie.split('; ').find(row => row.startsWith('jwt_token='));
        const headers = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token.split('=')[1]}`;
        }
        
        const response = await fetch("/api/importar-empleados", {
            method: "POST",
            headers: headers,
            body: formData
        });
        if (response.ok) {
            alert("Empleados importados correctamente");
        } else {
            alert("Error al importar empleados");
        }
    };
    input.click();
}

async function exportarEmpleados() {
    const token = document.cookie.split('; ').find(row => row.startsWith('jwt_token='));
    const headers = {};
    if (token) {
        headers['Authorization'] = `Bearer ${token.split('=')[1]}`;
    }

    const response = await fetch("/api/exportar-empleados", {
        method: "GET",
        headers: headers
    });

    if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `empleados_${new Date().toISOString().slice(0,10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } else {
        alert("Error al exportar empleados");
    }
}

setInterval(actualizarRegistros, 5000);
