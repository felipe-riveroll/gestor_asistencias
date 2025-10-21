document.addEventListener("DOMContentLoaded", function () {
    // 1. Constantes para elementos del DOM
    const fechaInicio = document.getElementById("fechaInicio");
    const fechaFin = document.getElementById("fechaFin");
    const buscarEmpleado = document.getElementById("buscarEmpleado");
    const sucursalSelect = document.getElementById("sucursal");
    const detalleHeader = document.getElementById("tablaDetalleHeader");
    const detalleBody = document.getElementById("detalleBody");
    const retardosBody = document.getElementById("retardosBody");
    const btnPDF = document.getElementById("btnPDF");
    const btnExcel = document.getElementById("btnExcel");
    const btnCSV = document.getElementById("btnCSV");
    const tabDetalle = document.getElementById("tabDetalle");
    const tabRetardos = document.getElementById("tabRetardos");
    const sectionDetalle = document.getElementById("Detalle");
    const sectionRetardos = document.getElementById("Retardos");
    
    // Agrupación de botones de exportación para DRY (Don't Repeat Yourself)
    const botonesExportacion = [btnPDF, btnExcel, btnCSV];

    let todasLasAsistencias = [];

    // --- Funciones de Lógica Principal ---

    /**
     * Carga los datos de asistencia desde la API.
     */
    async function cargarDatos() {
        // Mostrar estado de carga y deshabilitar botones
        const mensajeCargando = '<tr><td colspan="10" style="text-align: center;">Cargando...</td></tr>';
        detalleBody.innerHTML = mensajeCargando;
        retardosBody.innerHTML = mensajeCargando.replace('10', '8');
        botonesExportacion.forEach(btn => btn.disabled = true);

        const params = {
            startDate: fechaInicio.value,
            endDate: fechaFin.value,
            sucursal: sucursalSelect.value,
        };

        // Validación inicial de parámetros
        if (!params.startDate || !params.endDate || !params.sucursal) {
            const msg = '<tr><td colspan="10" style="text-align: center;">Por favor, selecciona fechas y sucursal.</td></tr>';
            detalleBody.innerHTML = msg;
            retardosBody.innerHTML = msg.replace('10', '8');
            return;
        }

        // 🚨 CORRECCIÓN: Uso correcto de template literals (backticks ``) para la URL.
        const url = `/api/reporte_detalle/?${new URLSearchParams(params)}`;

        try {
            const response = await fetch(url);
            if (!response.ok) { // Mejor manejo de errores HTTP (404, 500, etc.)
                throw new Error(`Error en la solicitud: ${response.statusText}`);
            }
            const resultado = await response.json();
            
            if (!resultado.success) {
                // El servidor respondió OK (200) pero la lógica indica un error
                throw new Error(resultado.error || 'Error desconocido al obtener datos.');
            }
            
            todasLasAsistencias = resultado.data || [];
            filtrarYRenderizar();

        } catch (error) {
            console.error("Error al cargar datos:", error);
            const errorMsg = `<tr><td colspan="10" style="text-align: center;">Error: ${error.message}</td></tr>`;
            detalleBody.innerHTML = errorMsg;
            retardosBody.innerHTML = errorMsg.replace('10', '8'); // Reemplazar para col-span
        }
    }

    /**
     * Filtra los datos cargados en base a la búsqueda y renderiza ambas tablas.
     */
    function filtrarYRenderizar() {
        const busqueda = buscarEmpleado.value.toLowerCase().trim();
        
        // Uso de Optional Chaining y Nullish Coalescing para mayor seguridad
        const datosFiltrados = todasLasAsistencias.filter(item => {
            if (!busqueda) return true;
            const nombre = (item.Nombre ?? '').toLowerCase();
            const id = (item.employee ?? '').toString().toLowerCase();
            return nombre.includes(busqueda) || id.includes(busqueda);
        });

        // Filtrar retardos específicos
        const datosRetardos = datosFiltrados.filter(item => 
            item.observacion_incidencia === 'Retardo Normal' || item.observacion_incidencia === 'Retardo Mayor'
        );
        
        pintarTablaDetalle(datosFiltrados);
        pintarTablaRetardos(datosRetardos);
        
        const hayDatos = datosFiltrados.length > 0;
        botonesExportacion.forEach(btn => btn.disabled = !hayDatos);
    }

    /**
     * Renderiza la tabla de Detalle de Asistencias.
     * @param {Array} datos - Los datos a mostrar.
     */
    function pintarTablaDetalle(datos) {
        detalleHeader.innerHTML = "";
        detalleBody.innerHTML = "";
        
        if (datos.length === 0) {
            detalleHeader.innerHTML = '<tr><th>Información</th></tr>';
            detalleBody.innerHTML = '<tr><td colspan="10" style="text-align: center;">No se encontraron registros.</td></tr>';
            return;
        }
        
        // Determinar el máximo de checadas dinámicamente
        let maxChecadas = 0;
        datos.forEach(d => {
            // Se asume que 'checado_1', 'checado_2', etc. son las checadas intermedias
            const checadasKeys = Object.keys(d).filter(key => key.startsWith('checado_') && key !== 'checado_primero' && key !== 'checado_ultimo');
            if (checadasKeys.length > maxChecadas) maxChecadas = checadasKeys.length;
        });
        
        // Asegurar un mínimo de 2 columnas para Checados (Entrada/Salida)
        maxChecadas = Math.max(maxChecadas, 2); 

        // Generar encabezados de la tabla
        let headersHTML = `<th>ID</th><th>Nombre</th><th>Fecha</th><th>Día</th><th>H. Esperadas</th><th>H. Trabajadas</th>`;
        for (let i = 1; i <= maxChecadas; i++) {
            headersHTML += `<th>Checado ${i}</th>`;
        }
        headersHTML += `<th>Observaciones</th>`;
        detalleHeader.innerHTML = `<tr>${headersHTML}</tr>`;

        // Llenar el cuerpo de la tabla
        let rowsHTML = datos.map(d => {
            const observacion = d.observacion_incidencia || 'OK';
            let className = '';
            
            // Usar un objeto mapa para los nombres de clase, más limpio que el switch
            const classMap = {
                'Falta': 'fila-falta', 'Permiso': 'fila-permiso', 
                'Retardo Normal': 'fila-retardo-normal', 'Retardo Mayor': 'fila-retardo-mayor',
                'Cumplió con horas': 'fila-retardo-cumplido', 'Salida Anticipada': 'fila-salida-anticipada',
                'Descanso': 'fila-descanso'
            };
            className = classMap[observacion] || '';

            let rowData = `<td>${d.employee ?? ''}</td><td>${d.Nombre ?? ''}</td><td>${d.dia ?? ''}</td><td>${d.dia_semana ?? ''}</td><td>${d.horas_esperadas ?? '00:00:00'}</td><td>${d.duration ?? '00:00:00'}</td>`;
            for (let i = 1; i <= maxChecadas; i++) {
                rowData += `<td>${d['checado_' + i] ?? '-'}</td>`;
            }
            rowData += `<td>${observacion}</td>`;

            return `<tr class="${className}">${rowData}</tr>`;
        }).join('');

        detalleBody.innerHTML = rowsHTML;
    }

    /**
     * Renderiza la tabla de Retardos.
     * @param {Array} datos - Los datos de retardos a mostrar.
     */
    function pintarTablaRetardos(datos) {
        retardosBody.innerHTML = "";
        
        if (datos.length === 0) {
            retardosBody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No hay retardos.</td></tr>';
            return;
        }

        let rowsHTML = datos.map(d => {
            const className = d.observacion_incidencia === 'Retardo Mayor' ? 'fila-retardo-mayor' : 'fila-retardo-normal';
            return `
                <tr class="${className}">
                    <td>${d.employee ?? ''}</td>
                    <td>${d.Nombre ?? ''}</td>
                    <td>${d.Sucursal ?? 'N/A'}</td>
                    <td>${d.dia ?? ''}</td>
                    <td>${d.dia_semana ?? ''}</td>
                    <td>${d.horario_entrada ?? '-'}</td>
                    <td>${d.checado_primero ?? '-'}</td>
                    <td>${d.observacion_incidencia}</td>
                </tr>
            `;
        }).join('');
        
        retardosBody.innerHTML = rowsHTML;
    }
    
    /**
     * Controla el cambio de pestañas.
     * @param {Event} evt - Evento de click.
     */
    function switchTab(evt) {
        // Mejor práctica: obtener el ID de la sección directamente
        const tabId = evt.currentTarget.id;
        const sectionId = tabId.replace('tab', ''); // 'tabDetalle' -> 'Detalle'

        [tabDetalle, tabRetardos].forEach(tab => tab.classList.remove('active'));
        [sectionDetalle, sectionRetardos].forEach(sec => sec.style.display = 'none');
        
        evt.currentTarget.classList.add('active');
        document.getElementById(sectionId).style.display = 'block';
    }
    
    // Función de utilidades para Cookies (CSRF Token)
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // ¿Empieza con el nombre?
                if (cookie.startsWith(name + '=')) { 
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // --- Funciones de Exportación ---

    /**
     * Función principal para exportar.
     * @param {string} formato - Formato a exportar ('xlsx', 'csv', 'pdf').
     */
    function exportarA(formato) {
        const nombreArchivoBase = 'reporte_asistencias';
        const fecha = new Date().toISOString().split('T')[0];
        const nombreArchivoFinal = `${nombreArchivoBase}_${fecha}`;

        try {
            switch (formato) {
                case 'xlsx':
                    exportarExcelMultiHoja(nombreArchivoFinal);
                    break;
                case 'csv':
                    exportarTablaActualCSV(nombreArchivoFinal);
                    break;
                case 'pdf':
                    exportarTablaActualPDF(nombreArchivoFinal);
                    break;
                default:
                    console.warn(`Formato de exportación no soportado: ${formato}`);
            }
        } catch (error) {
            console.error("Error al exportar:", error);
            alert(`Ocurrió un error al intentar exportar: ${error.message}`);
        }
    }
    
    /**
     * Extrae los datos (headers y body) de una tabla.
     * @param {HTMLElement} tableHeader - El thead del elemento tabla.
     * @param {HTMLElement} tableBody - El tbody del elemento tabla.
     * @returns {{datos: Array<Array<string>>, colores: Array<string>}|null}
     */
    function obtenerDatosDeTabla(tableHeader, tableBody) {
        const filas = tableBody.querySelectorAll('tr');
        // Si no hay filas o la única fila es el mensaje de "no datos" (colspan > 1)
        if (filas.length === 0 || (filas.length === 1 && (filas[0].querySelector('td')?.colSpan ?? 0) > 1)) {
            return null;
        }
        
        const headers = Array.from(tableHeader.querySelectorAll('th')).map(th => th.textContent.trim());
        const datos = [headers];
        
        const colores = [];

        filas.forEach(fila => {
            const celdas = Array.from(fila.querySelectorAll('td'));
            datos.push(celdas.map(td => td.textContent.trim()));
            
            // Obtener la clase de color para la fila
            const colorClass = Array.from(fila.classList).find(cls => cls.startsWith('fila-')) || '';
            colores.push(colorClass);
        });
        
        return { datos, colores };
    }

    // Exportación a Excel (Multi-hoja con POST al servidor)
    function exportarExcelMultiHoja(nombreArchivo) {
        // Se asume que '#tablaRetardos thead' existe en el DOM
        const datosDetalle = obtenerDatosDeTabla(detalleHeader, detalleBody);
        const datosRetardos = obtenerDatosDeTabla(document.querySelector('#tablaRetardos thead'), retardosBody);
        
        const sheetsPayload = {};
        if (datosDetalle) sheetsPayload.detalle = datosDetalle;
        if (datosRetardos) sheetsPayload.retardos = datosRetardos;

        if (Object.keys(sheetsPayload).length === 0) {
            alert('No hay datos en ninguna de las pestañas para exportar.');
            return;
        }

        const exportData = {
            nombre_archivo: nombreArchivo,
            sheets: sheetsPayload
        };

        fetch('/api/exportar_excel_con_colores/', {
            method: 'POST',
            // Asegurar que 'X-CSRFToken' se use para peticiones POST en Django/similar
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') }, 
            body: JSON.stringify(exportData)
        })
        .then(response => {
            if (!response.ok) {
                // Leer el posible error JSON del servidor para mejor diagnóstico
                return response.json().then(err => { throw new Error(err.error || 'Error en la exportación del servidor'); });
            }
            return response.blob();
        })
        .then(blob => {
            // Descarga del archivo
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none'; a.href = url; a.download = `${nombreArchivo}.xlsx`;
            document.body.appendChild(a); a.click();
            window.URL.revokeObjectURL(url); a.remove(); // Usar a.remove() en lugar de document.body.removeChild(a)
        })
        .catch(error => {
             console.error("Error en la exportación a Excel:", error);
             alert(`Error al exportar a Excel: ${error.message}`);
        });
    }
    
    // Exportación a CSV
    function exportarTablaActualCSV(nombreArchivo) {
        if (typeof XLSX === 'undefined') {
            throw new Error("La librería de exportación a CSV (SheetJS) no está disponible.");
        }
        
        const tabActiva = document.querySelector('.tablinks.active')?.id;
        if (!tabActiva) {
            throw new Error("No se pudo determinar la pestaña activa.");
        }
        
        const data = tabActiva === 'tabDetalle' 
            ? obtenerDatosDeTabla(detalleHeader, detalleBody)
            : obtenerDatosDeTabla(document.querySelector('#tablaRetardos thead'), retardosBody);

        if (!data) {
            alert('No hay datos para exportar en la pestaña actual.');
            return;
        }
        
        const ws = XLSX.utils.aoa_to_sheet(data.datos);
        const csvContent = XLSX.utils.sheet_to_csv(ws);
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.setAttribute('download', `${nombreArchivo}_${tabActiva.replace('tab', '').toLowerCase()}.csv`);
        document.body.appendChild(link);
        link.click();
        link.remove(); // Usar link.remove()
    }
    
    // Exportación a PDF
    function exportarTablaActualPDF(nombreArchivo) {
        // Se asume que jspdf.jsPDF y jspdf-autotable ya están cargados en el scope global
        if (typeof window.jspdf === 'undefined' || typeof window.jspdf.jsPDF === 'undefined' || typeof doc?.autoTable === 'undefined') {
             throw new Error("La librería de exportación a PDF (jsPDF y autoTable) no está disponible o no está cargada correctamente.");
        }
        
        const tabActiva = document.querySelector('.tablinks.active')?.id;
        if (!tabActiva) {
            throw new Error("No se pudo determinar la pestaña activa.");
        }
        
        const data = tabActiva === 'tabDetalle' 
            ? obtenerDatosDeTabla(detalleHeader, detalleBody)
            : obtenerDatosDeTabla(document.querySelector('#tablaRetardos thead'), retardosBody);
        
        if (!data) {
            alert('No hay datos para exportar en la pestaña actual.');
            return;
        }

        const { jsPDF } = window.jspdf;
        const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
        
        // Mapa de colores (RGB)
        const colorMap = {
            'fila-falta': [255, 204, 204], // Rojo claro
            'fila-retardo-normal': [255, 242, 204], // Amarillo claro
            'fila-permiso': [212, 237, 218], // Verde claro
            'fila-retardo-cumplido': [230, 212, 237], // Morado claro
            'fila-descanso': [155, 89, 182], // Morado oscuro
            'fila-retardo-mayor': [255, 217, 102], // Amarillo medio
            'fila-salida-anticipada': [248, 203, 173], // Naranja claro
        };

        doc.autoTable({
            head: [data.datos[0]],
            body: data.datos.slice(1),
            startY: 20,
            styles: { fontSize: 7, cellPadding: 1.5 }, // Reducir tamaño de fuente/padding para landscape
            headStyles: { fillColor: [39, 174, 96], textColor: [255, 255, 255] },
            didParseCell: function(hookData) {
                if (hookData.section === 'body') {
                    // Obtener la clase de color de la fila, no de la celda
                    const cssClass = data.colores[hookData.row.index]; 
                    if (cssClass && colorMap[cssClass]) {
                        hookData.cell.styles.fillColor = colorMap[cssClass];
                        // Cambiar el color del texto para filas con fondo oscuro (ej. Descanso)
                        if (cssClass === 'fila-descanso') {
                            hookData.cell.styles.textColor = [255, 255, 255];
                        } else {
                            hookData.cell.styles.textColor = [0, 0, 0]; // Asegurar texto negro para otros
                        }
                    } else {
                         hookData.cell.styles.textColor = [0, 0, 0];
                         hookData.cell.styles.fillColor = [255, 255, 255];
                    }
                }
            },
            didDrawPage: function(data) {
                doc.setFontSize(16);
                doc.text("Reporte de Asistencias", data.settings.margin.left, 15);
            }
        });
        
        doc.save(`${nombreArchivo}_${tabActiva.replace('tab', '').toLowerCase()}.pdf`);
    }

    // --- Inicialización y Event Listeners ---

    // Eventos para recargar datos (cambio de fecha o sucursal)
    [fechaInicio, fechaFin, sucursalSelect].forEach(el => el.addEventListener("change", cargarDatos));
    
    // Evento para filtrar (tiempo real)
    buscarEmpleado.addEventListener("input", filtrarYRenderizar);
    
    // Eventos para el cambio de pestañas
    tabDetalle.addEventListener("click", switchTab);
    tabRetardos.addEventListener("click", switchTab);
    
    // Eventos para exportación
    btnExcel.addEventListener('click', () => exportarA('xlsx'));
    btnCSV.addEventListener('click', () => exportarA('csv'));
    btnPDF.addEventListener('click', () => exportarA('pdf'));

    // Establecer fechas por defecto (últimos 7 días) y cargar al inicio
    const today = new Date();
    const unaSemanaAtras = new Date();
    unaSemanaAtras.setDate(today.getDate() - 6);
    
    const formatDate = (date) => date.toISOString().split('T')[0];
    
    fechaInicio.value = formatDate(unaSemanaAtras);
    fechaFin.value = formatDate(today);
    
    // Simular click en la pestaña de Detalle para inicializar la vista (y sus estilos CSS)
    // Es mejor llamar a cargarDatos si queremos que la data se traiga desde el inicio.
    // Si la selección de sucursal es la que dispara `cargarDatos`, descomenta `tabDetalle.click()` si necesitas inicializar la vista de pestaña:
    tabDetalle.click(); 
    
    // Si la sucursal ya tiene un valor por defecto en el HTML, llama a cargarDatos:
    if (sucursalSelect.value) {
        cargarDatos();
    }
});