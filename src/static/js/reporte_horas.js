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
    
    // Formato YYYY-MM-DD para input[type="date"]
    startDateInput.value = sevenDaysAgo.toISOString().split('T')[0];
    endDateInput.value = today.toISOString().split('T')[0];

    async function cargarReporte() {
        // Opcional: Agregar una clase para mostrar un estado de carga visualmente
        // Por ejemplo: reporteBody.innerHTML = "<tr><td colspan='14'>Cargando...</td></tr>";
        
        try {
            console.log("🔄 Iniciando carga de reporte...");
            
            const startDate = startDateInput.value;
            const endDate = endDateInput.value;
            const sucursal = sucursalSelect.value;
            const empleado = empleadoInput.value.trim();

            console.log("📋 Parámetros:", { startDate, endDate, sucursal, empleado });

            if (!startDate || !endDate) {
                console.log("⏸️ Fechas no seleccionadas, pausando");
                reporteBody.innerHTML = "<tr><td colspan='14'>Selecciona un rango de fechas.</td></tr>";
                return;
            }

            const params = new URLSearchParams();
            params.append("startDate", startDate);
            params.append("endDate", endDate);
            if (sucursal) params.append("sucursal", sucursal);
            if (empleado) params.append("empleado", empleado);

            // ⚠️ CORRECCIÓN CLAVE: Se usó 'template literal' (backticks) para la URL
            const url = `/api/reporte_horas/?${params.toString()}`;
            console.log("🌐 URL completa:", url);

            console.log("📤 Enviando solicitud...");
            const response = await fetch(url);
            console.log("📥 Respuesta recibida. Status:", response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error("❌ Error del servidor:", errorText);
                
                // ⚠️ CORRECCIÓN CLAVE: Se usó 'template literal' (backticks) para el mensaje de error
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
                // ⚠️ CORRECCIÓN CLAVE: Se usó 'template literal' (backticks) para el log
                console.log(`📊 ${result.data.length} registros procesados`);
                mostrarDatos(result.data);
            } else {
                console.warn("⚠️ No hay datos o formato incorrecto:", result);
                reporteBody.innerHTML = "<tr><td colspan='14'>No se encontraron datos o el formato es incorrecto.</td></tr>";
            }
            
        } catch (err) {
            console.error("💥 Error completo:", err);
            // Opcional: Mostrar un mensaje menos intrusivo que 'alert'
            reporteBody.innerHTML = `<tr><td colspan='14' style="color: red;">Error al cargar: ${err.message}</td></tr>`;
            // alert("Error: " + err.message); // Mantenemos el alert original, pero se sugiere mejor UX
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
            // Nota: Los campos de aquí deben ser revisados con el output real de tu API.
            // Se mantiene la estructura original ya que es una presunción de tu API.
            // ⚠️ CORRECCIÓN CLAVE: Se corrigieron los backticks del template literal.
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

    // Asegúrate de que la librería 'xlsx' (sheet.js) esté cargada en tu HTML.
    function downloadExcel() {
        if (typeof XLSX === 'undefined') {
            alert("Error: La librería XLSX (SheetJS) no está cargada.");
            return;
        }

        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        const sucursal = sucursalSelect.value;
        
        const wb = XLSX.utils.book_new();
        // Intentar obtener los encabezados de la tabla
        const headersElement = document.querySelectorAll("#reporteTable thead th");
        if (headersElement.length === 0) {
            console.warn("No se encontraron encabezados de tabla para el reporte.");
            // Si no hay encabezados, salimos o usamos un set predefinido
            alert("Advertencia: No se encontraron encabezados de tabla. Asegúrate de que la tabla 'reporteTable' esté bien definida.");
            return; 
        }

        const headers = Array.from(headersElement).map(th => th.textContent.trim());
        const wsData = [headers];

        // Obtener datos del cuerpo de la tabla
        document.querySelectorAll("#reporteTable tbody tr").forEach(tr => {
            const row = Array.from(tr.querySelectorAll("td")).map(td => td.textContent.trim());
            // Solo añadir filas que contengan datos, no las de 'No se encontraron registros'
            if (row.length > 1 && !row[0].includes("No se encontraron")) {
                wsData.push(row);
            }
        });

        const ws = XLSX.utils.aoa_to_sheet(wsData);
        XLSX.utils.book_append_sheet(wb, ws, "Reporte");
        
        // ⚠️ CORRECCIÓN CLAVE: Se usó 'template literal' (backticks) para el nombre del archivo
        const fileName = `reporte_horas_${startDate}_a_${endDate}_${sucursal || 'Todas'}.xlsx`;
        XLSX.writeFile(wb, fileName);
    }

    // Event listeners
    startDateInput.addEventListener("change", cargarReporte);
    endDateInput.addEventListener("change", cargarReporte);
    // Nota: El evento 'change' en un select es más apropiado que 'input'
    sucursalSelect.addEventListener("change", cargarReporte); 
    // Usar 'input' permite un filtrado inmediato mientras el usuario escribe
    empleadoInput.addEventListener("input", cargarReporte); 
    downloadBtn.addEventListener("click", downloadExcel);

    // Carga inicial
    cargarReporte();
});