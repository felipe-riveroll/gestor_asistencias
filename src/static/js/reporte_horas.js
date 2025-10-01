document.addEventListener("DOMContentLoaded", () => {
    const startDateInput = document.getElementById("startDate");
    const endDateInput = document.getElementById("endDate");
    const sucursalSelect = document.getElementById("sucursal");
    const empleadoInput = document.getElementById("empleado");
    const downloadBtn = document.getElementById("downloadBtn");
    const reporteBody = document.getElementById("reporteBody");

    if (!startDateInput || !endDateInput || !sucursalSelect || !empleadoInput || !downloadBtn || !reporteBody) {
        console.error("Algún elemento no fue encontrado en el DOM. Revisa los id del HTML.");
        return;
    }

    // Establecer fechas por defecto (hoy y hace 7 días)
    const today = new Date();
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(today.getDate() - 7);
    
    startDateInput.value = sevenDaysAgo.toISOString().split('T')[0];
    endDateInput.value = today.toISOString().split('T')[0];

    async function cargarReporte() {
        try {
            console.log("🔄 Iniciando carga de reporte...");
            
            const startDate = startDateInput.value;
            const endDate = endDateInput.value;
            const sucursal = sucursalSelect.value;
            const empleado = empleadoInput.value.trim();

            console.log("📋 Parámetros:", { startDate, endDate, sucursal, empleado });

            if (!startDate || !endDate) {
                console.log("⏸️ Fechas no seleccionadas, pausando");
                return;
            }

            const params = new URLSearchParams();
            params.append("startDate", startDate);
            params.append("endDate", endDate);
            if (sucursal) params.append("sucursal", sucursal);
            if (empleado) params.append("empleado", empleado);

            // CORRECCIÓN: La URL correcta es /api/reporte_horas/ (no /api/reporte-horas/)
            const url = `/api/reporte_horas/?${params.toString()}`;
            console.log("🌐 URL completa:", url);

            console.log("📤 Enviando solicitud...");
            const response = await fetch(url);
            console.log("📥 Respuesta recibida. Status:", response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error("❌ Error del servidor:", errorText);
                
                let errorMessage = `Error ${response.status}`;
                try {
                    const errorData = JSON.parse(errorText);
                    errorMessage += `: ${errorData.error || errorData.details || response.statusText}`;
                } catch {
                    errorMessage += `: ${errorText.substring(0, 100)}...`;
                }
                
                throw new Error(errorMessage);
            }

            const result = await response.json();
            console.log("✅ Datos recibidos:", result);
            
            if (result.data && Array.isArray(result.data)) {
                console.log(`📊 ${result.data.length} registros procesados`);
                mostrarDatos(result.data);
            } else {
                console.warn("⚠️ No hay datos o formato incorrecto:", result);
                reporteBody.innerHTML = "<tr><td colspan='14'>No se encontraron datos</td></tr>";
            }
            
        } catch (err) {
            console.error("💥 Error completo:", err);
            alert("Error: " + err.message);
        }
    }

    function mostrarDatos(datos) {
        reporteBody.innerHTML = "";
        
        if (datos.length === 0) {
            reporteBody.innerHTML = "<tr><td colspan='14'>No se encontraron registros para los filtros seleccionados</td></tr>";
            return;
        }
        
        datos.forEach(d => {
            const row = document.createElement("tr");
            // CORRECCIÓN: Los nombres de campos deben coincidir con lo que devuelve tu API
            row.innerHTML = `
                <td>${d.employee || ''}</td>
                <td>${d.Nombre || 'Sin nombre'}</td>
                <td>${d.total_horas_trabajadas || '00:00:00'}</td>
                <td>${d.total_horas_esperadas || '08:00:00'}</td>
                <td>${d.total_horas_descontadas_permiso || '00:00:00'}</td>
                <td>${d.total_horas_descanso || '00:00:00'}</td>
                <td>${d.total_horas || '00:00:00'}</td>
                <td>${d.total_retardos || '00:00:00'}</td>
                <td>${d.faltas_del_periodo || '0'}</td>
                <td>${d.faltas_justificadas || '0'}</td>
                <td>${d.total_faltas || '0'}</td>
                <td>${d.episodios_ausencia || '0'}</td>
                <td>${d.total_salidas_anticipadas || '00:00:00'}</td>
                <td>${d.diferencia_HHMMSS || '00:00:00'}</td>
            `;
            reporteBody.appendChild(row);
        });
    }

    function downloadExcel() {
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        const sucursal = sucursalSelect.value;
        
        const wb = XLSX.utils.book_new();
        const headers = Array.from(document.querySelectorAll("#reporteTable thead th")).map(th => th.textContent);
        const wsData = [headers];

        document.querySelectorAll("#reporteTable tbody tr").forEach(tr => {
            const row = Array.from(tr.querySelectorAll("td")).map(td => td.textContent);
            wsData.push(row);
        });

        const ws = XLSX.utils.aoa_to_sheet(wsData);
        XLSX.utils.book_append_sheet(wb, ws, "Reporte");
        
        const fileName = `reporte_horas_${startDate}_a_${endDate}_${sucursal}.xlsx`;
        XLSX.writeFile(wb, fileName);
    }

    // Event listeners
    startDateInput.addEventListener("change", cargarReporte);
    endDateInput.addEventListener("change", cargarReporte);
    sucursalSelect.addEventListener("change", cargarReporte);
    empleadoInput.addEventListener("input", cargarReporte);
    downloadBtn.addEventListener("click", downloadExcel);

    // Carga inicial
    cargarReporte();
});