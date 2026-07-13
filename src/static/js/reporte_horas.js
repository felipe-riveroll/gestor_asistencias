// --- FUNCIÓN DE AYUDA PARA EL TOKEN DE DJANGO ---
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    if (cookieValue === null) { const m = document.querySelector('meta[name="csrf-token"]'); if (m) cookieValue = m.getAttribute('content'); }
    return cookieValue;
}
document.addEventListener("DOMContentLoaded", () => {
    // --- Referencias a los elementos de TU HTML ---
    const startDateInput = document.getElementById("startDate");
    const endDateInput = document.getElementById("endDate");
    const sucursalSelect = document.getElementById("sucursal");
    const empleadoInput = document.getElementById("empleado");
    const downloadBtn = document.getElementById("downloadBtn");
    const reporteBody = document.getElementById("reporteBody"); 

    if (!startDateInput || !endDateInput || !sucursalSelect || !empleadoInput || !downloadBtn || !reporteBody) {
        console.error("❌ Algún elemento no fue encontrado en el DOM. Revisa los IDs del HTML.");
        // Opcional: Deshabilitar la interfaz si faltan elementos cruciales
        // downloadBtn.disabled = true; 
        return; 
    }

    let datosCompletosDelReporte = []; // Para guardar los datos originales del API

    /**
     * Carga los datos del reporte desde la API.
     */
    async function cargarReporte() {
        // Muestra un mensaje de carga antes de la petición
        reporteBody.innerHTML = '<tr><td colspan="14">Cargando...</td></tr>';
        console.log("🔄 Iniciando carga de reporte...");

        const params = {
            startDate: startDateInput.value,
            endDate: endDateInput.value,
            // sucursal: sucursalSelect.value, // Dejé este parámetro comentado por si su valor puede ser vacío/nulo.
            sucursal: sucursalSelect.value === 'all' ? '' : sucursalSelect.value, // Mejor manejo de 'todos'
        };

        if (!params.startDate || !params.endDate) {
            reporteBody.innerHTML = '<tr><td colspan="14">Selecciona un rango de fechas.</td></tr>';
            return;
        }

        // 🟢 CORRECCIÓN 1: Se corrigió la sintaxis de la plantilla de cadena (template literal) para la URL.
        const url = `/api/reporte_horas/?${new URLSearchParams(params)}`;

        try {
            const response = await fetch(url);
            const resultado = await response.json();
            
            // 🟢 CORRECCIÓN 2: Uso de sintaxis correcta para template literal dentro de un `throw new Error`.
            if (!response.ok) throw new Error(resultado.error || `Error ${response.status}`);

            datosCompletosDelReporte = resultado.data || [];
            filtrarTabla(); // Llama a filtrar para aplicar la búsqueda actual sobre los nuevos datos

        } catch (err) {
            console.error("💥 Error al cargar el reporte:", err);
            // 🟢 CORRECCIÓN 3: Uso de sintaxis correcta para template literal para mostrar el error.
            reporteBody.innerHTML = `<tr><td colspan="14">Error al cargar el reporte: ${err.message}</td></tr>`;
        }
    }

    /**
     * Renderiza la tabla con los datos proporcionados.
     * @param {Array<Object>} datos - Los datos a mostrar en la tabla.
     */
    function renderizarTabla(datos) {
        reporteBody.innerHTML = "";
        if (datos.length === 0) {
            // 🟢 CORRECCIÓN 4: Corregido el atributo 'colspan' de 'colspan-' a 'colspan'.
            reporteBody.innerHTML = "<tr><td colspan='14'>No se encontraron registros.</td></tr>";
            return;
        }
        
        // Uso de `map` y `join` para una renderización más eficiente y limpia (QoL)
        const filasHTML = datos.map(d => `
            <tr>
                <td>${d.employee || ''}</td>
                <td>${d.Nombre || 'Sin nombre'}</td>
                <td>${d.total_horas_trabajadas || '00:00:00'}</td>
                <td>${d.total_horas_esperadas || '00:00:00'}</td>
                <td>${d.total_horas_descontadas_permiso || '00:00:00'}</td>
                <td>${d.total_horas_descanso || '00:00:00'}</td>
                <td>${d.total_horas || '00:00:00'}</td>
                <td>${d.total_retardos || 0}</td>
                <td>${d.faltas_del_periodo || 0}</td>
                <td>${d.faltas_justificadas || 0}</td>
                <td>${d.total_faltas || 0}</td>
                <td>${d.episodios_ausencia || 0}</td>
                <td>${d.total_salidas_anticipadas || 0}</td>
                <td>${d.diferencia_HHMMSS || '00:00:00'}</td>
            </tr>
        `).join('');
        
        reporteBody.innerHTML = filasHTML;
    }

    /**
     * Filtra los datos cargados localmente según el texto de búsqueda del empleado.
     */
    function filtrarTabla() {
        const textoBusqueda = empleadoInput.value.toLowerCase().trim();
        const datosFiltrados = datosCompletosDelReporte.filter(empleado => {
            if (!textoBusqueda) return true; 

            // Se busca en el Nombre o en el ID de empleado (más robusto)
            const nombre = (empleado.Nombre || '').toLowerCase();
            const id = (empleado.employee || '').toString().toLowerCase(); 
            
            return nombre.includes(textoBusqueda) || id.includes(textoBusqueda);
        });
        
        renderizarTabla(datosFiltrados);
    }

    /**
     * Exporta los datos de la tabla a un archivo Excel llamando al backend.
     */
    async function downloadExcel() {
        console.log("Iniciando exportación con el método del backend...");
        
        // 1. Obtener los encabezados (Headers) desde la tabla HTML
        const headers = Array.from(document.querySelectorAll("#reporteTable thead th"))
                             .map(th => th.innerText.trim());
        
        if (headers.length === 0) {
             alert("Error: No se pudieron encontrar los encabezados de la tabla.");
             return;
        }

        // 2. Obtener los datos (usamos los datos ya filtrados por el buscador)
        const textoBusqueda = empleadoInput.value.toLowerCase().trim();
        const datosParaExportar = datosCompletosDelReporte.filter(empleado => {
             if (!textoBusqueda) return true; // Si no hay búsqueda, incluir todos
             const nombre = (empleado.Nombre || '').toLowerCase();
             const id = (empleado.employee || '').toString().toLowerCase(); 
             return nombre.includes(textoBusqueda) || id.includes(textoBusqueda);
        });

        // 3. Convertir los datos (array de objetos) a (array de arrays)
        // El orden debe ser el mismo que en tu función renderizarTabla
        const dataRows = datosParaExportar.map(d => [
            d.employee || '',
            d.Nombre || 'Sin nombre',
            d.total_horas_trabajadas || '00:00:00',
            d.total_horas_esperadas || '00:00:00',
            d.total_horas_descontadas_permiso || '00:00:00',
            d.total_horas_descanso || '00:00:00',
            d.total_horas || '00:00:00',
            d.total_retardos || 0,
            d.faltas_del_periodo || 0,
            d.faltas_justificadas || 0,
            d.total_faltas || 0,
            d.episodios_ausencia || 0,
            d.total_salidas_anticipadas || 0,
            d.diferencia_HHMMSS || '00:00:00'
        ]);

        // 4. Construir el objeto JSON para enviar a Django
        const nombreDelArchivo = `Reporte_Horas_${startDateInput.value}_a_${endDateInput.value}`;
        const exportData = {
            nombre_archivo: nombreDelArchivo,
            sheets: {
                "Reporte": {
                    "datos": [headers, ...dataRows], // Unimos los headers + las filas de datos
                    "colores": [] // Este reporte no tiene colores de fila, mandamos un array vacío
                }
            }
        };

        // 5. Hacer la petición POST al backend (¡aquí está la magia!)
        try {
            // Deshabilitar el botón para evitar doble clic
            downloadBtn.innerText = "Descargando";
            downloadBtn.disabled = true;

            const response = await fetch('/api/exportar_excel_con_colores/', { // Esta es la URL de tu vista
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken') // <-- ¡MUY IMPORTANTE para Django!
                },
                body: JSON.stringify(exportData)
            });

            if (!response.ok) {
                // Si el backend da un error, lo mostramos
                const err = await response.json();
                throw new Error(err.error || 'Error al generar el archivo en el servidor');
            }

            // 6. Descargar el archivo que nos manda el backend
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `${nombreDelArchivo}.xlsx`; // El nombre del archivo
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();

        } catch (err) {
            console.error("Error en la exportación del backend:", err);
            alert(`Error al exportar: ${err.message}`);
        } finally {
            // Volver a habilitar el botón
            downloadBtn.innerHTML = '<i class="fas fa-file-excel"></i> Descargar Excel';
            downloadBtn.disabled = false;
        }
    }
    // --- ASIGNACIÓN DE EVENTOS ---
    startDateInput.addEventListener("change", cargarReporte);
    endDateInput.addEventListener("change", cargarReporte);
    sucursalSelect.addEventListener("change", cargarReporte);
    empleadoInput.addEventListener("input", filtrarTabla); 
    downloadBtn.addEventListener("click", downloadExcel);

    // --- LÓGICA DE CARGA INICIAL ---
    const today = new Date();
    const oneMonthAgo = new Date(); // <-- 1. LÍNEA CAMBIADA
    oneMonthAgo.setMonth(today.getMonth() - 1); 
    
    // Función auxiliar para obtener la fecha en formato YYYY-MM-DD (QoL)
    const formatDate = date => date.toISOString().split('T')[0];

    // Establecer los valores por defecto
    startDateInput.value = formatDate(oneMonthAgo);
    endDateInput.value = formatDate(today);
    
    // Iniciar la carga del reporte con las fechas predeterminadas
    cargarReporte();
});