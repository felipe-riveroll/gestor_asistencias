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
     * Exporta los datos de la tabla a un archivo Excel.
     */
    function downloadExcel() {
        // 🟢 MEJORA (QoL): Se agrega una comprobación más robusta para la tabla.
        const tabla = document.getElementById('reporteTable');
        if (typeof XLSX === 'undefined' || !tabla) {
            return alert("La librería para exportar a Excel no está disponible o la tabla no existe.");
        }
        
        const wb = XLSX.utils.table_to_book(tabla, { sheet: "Reporte" });
        // 🟢 CORRECCIÓN 5: Uso de sintaxis correcta para template literal en el nombre del archivo.
        const fileName = `Reporte_${startDateInput.value}_a_${endDateInput.value}.xlsx`; 
        XLSX.writeFile(wb, fileName);
    }

    // --- ASIGNACIÓN DE EVENTOS ---
    startDateInput.addEventListener("change", cargarReporte);
    endDateInput.addEventListener("change", cargarReporte);
    sucursalSelect.addEventListener("change", cargarReporte);
    empleadoInput.addEventListener("input", filtrarTabla); 
    downloadBtn.addEventListener("click", downloadExcel);

    // --- LÓGICA DE CARGA INICIAL ---
    const today = new Date();
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(today.getDate() - 6);
    
    // Función auxiliar para obtener la fecha en formato YYYY-MM-DD (QoL)
    const formatDate = date => date.toISOString().split('T')[0];

    // Establecer los valores por defecto
    startDateInput.value = formatDate(sevenDaysAgo);
    endDateInput.value = formatDate(today);
    
    // Iniciar la carga del reporte con las fechas predeterminadas
    cargarReporte();
});