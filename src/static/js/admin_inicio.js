document.addEventListener("DOMContentLoaded", function () {
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

    let todasLasAsistencias = [];

    async function cargarDatos() {
        detalleBody.innerHTML = '<tr><td colspan="10" style="text-align: center;">Cargando...</td></tr>';
        retardosBody.innerHTML = '<tr><td colspan="8" style="text-align: center;">Cargando...</td></tr>';
        [btnPDF, btnExcel, btnCSV].forEach(btn => btn.disabled = true);
        const params = {
            startDate: fechaInicio.value,
            endDate: fechaFin.value,
            sucursal: sucursalSelect.value,
        };
        if (!params.startDate || !params.endDate || !params.sucursal) {
            const msg = '<tr><td colspan="10" style="text-align: center;">Por favor, selecciona fechas y sucursal.</td></tr>';
            detalleBody.innerHTML = msg;
            retardosBody.innerHTML = msg.replace('10', '8');
            return;
        }
        const url = `/api/reporte_detalle/?${new URLSearchParams(params)}`;
        try {
            const response = await fetch(url);
            const resultado = await response.json();
            if (!resultado.success) throw new Error(resultado.error || 'Error desconocido del servidor');
            todasLasAsistencias = resultado.data || [];
            filtrarYRenderizar();
        } catch (error) {
            const errorMsg = `<tr><td colspan="10" style="text-align: center;">Error: ${error.message}</td></tr>`;
            detalleBody.innerHTML = errorMsg;
            retardosBody.innerHTML = errorMsg.replace('10', '8');
        }
    }

    function filtrarYRenderizar() {
        const busqueda = buscarEmpleado.value.toLowerCase().trim();
        const datosFiltrados = todasLasAsistencias.filter(item => {
            if (!busqueda) return true;
            const nombre = (item.Nombre || '').toLowerCase();
            const id = (item.employee || '').toString().toLowerCase();
            return nombre.includes(busqueda) || id.includes(busqueda);
        });
        const datosRetardos = datosFiltrados.filter(item => 
            item.observacion_incidencia === 'Retardo Normal' || item.observacion_incidencia === 'Retardo Mayor'
        );
        pintarTablaDetalle(datosFiltrados);
        pintarTablaRetardos(datosRetardos);
        const hayDatos = datosFiltrados.length > 0;
        [btnPDF, btnExcel, btnCSV].forEach(btn => btn.disabled = !hayDatos);
    }

    function pintarTablaDetalle(datos) {
        detalleHeader.innerHTML = "";
        detalleBody.innerHTML = "";
        if (datos.length === 0) {
            detalleHeader.innerHTML = '<tr><th>Información</th></tr>';
            detalleBody.innerHTML = '<tr><td colspan="10" style="text-align: center;">No se encontraron registros.</td></tr>';
            return;
        }
        let maxChecadas = 0;
        datos.forEach(d => {
            const checadasKeys = Object.keys(d).filter(key => key.startsWith('checado_') && key !== 'checado_primero' && key !== 'checado_ultimo');
            if (checadasKeys.length > maxChecadas) maxChecadas = checadasKeys.length;
        });
        if (maxChecadas < 2) maxChecadas = 2;
        let headersHTML = `<th>ID</th><th>Nombre</th><th>Fecha</th><th>Día</th><th>H. Esperadas</th><th>H. Trabajadas</th>`;
        for (let i = 1; i <= maxChecadas; i++) headersHTML += `<th>Checado ${i}</th>`;
        headersHTML += `<th>Observaciones</th>`;
        detalleHeader.innerHTML = `<tr>${headersHTML}</tr>`;
        datos.forEach(d => {
            const tr = document.createElement("tr");
            const observacion = d.observacion_incidencia || 'OK';
            
            switch (observacion) {
                case 'Falta': tr.className = 'fila-falta'; break;
                case 'Permiso': tr.className = 'fila-permiso'; break;
                case 'Retardo Normal': tr.className = 'fila-retardo-normal'; break;
                case 'Retardo Mayor': tr.className = 'fila-retardo-mayor'; break;
                case 'Cumplió con horas': tr.className = 'fila-retardo-cumplido'; break;
                case 'Salida Anticipada': tr.className = 'fila-salida-anticipada'; break;
                case 'Descanso': tr.className = 'fila-descanso'; break;
            }
            
            let rowHTML = `<td>${d.employee||''}</td><td>${d.Nombre||''}</td><td>${d.dia||''}</td><td>${d.dia_semana||''}</td><td>${d.horas_esperadas||'00:00:00'}</td><td>${d.duration||'00:00:00'}</td>`;
            for (let i = 1; i <= maxChecadas; i++) rowHTML += `<td>${d['checado_'+i]||'-'}</td>`;
            rowHTML += `<td>${observacion}</td>`;
            tr.innerHTML = rowHTML;
            detalleBody.appendChild(tr);
        });
    }

    function pintarTablaRetardos(datos) {
        retardosBody.innerHTML = "";
        if (datos.length === 0) {
            retardosBody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No hay retardos.</td></tr>';
            return;
        }
        datos.forEach(d => {
            const tr = document.createElement("tr");
            tr.className = d.observacion_incidencia === 'Retardo Mayor' ? 'fila-retardo-mayor' : 'fila-retardo-normal';
            tr.innerHTML = `<td>${d.employee||''}</td><td>${d.Nombre||''}</td><td>${d.Sucursal||'N/A'}</td><td>${d.dia||''}</td><td>${d.dia_semana||''}</td><td>${d.horario_entrada||'-'}</td><td>${d.checado_primero||'-'}</td><td>${d.observacion_incidencia}</td>`;
            retardosBody.appendChild(tr);
        });
    }
    
    function switchTab(evt) {
        const tabId = evt.currentTarget.id;
        [tabDetalle, tabRetardos].forEach(tab => tab.classList.remove('active'));
        [sectionDetalle, sectionRetardos].forEach(sec => sec.style.display = 'none');
        evt.currentTarget.classList.add('active');
        document.getElementById(tabId.replace('tab', '')).style.display = 'block';
    }
    
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
        return cookieValue;
    }

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
            }
        } catch (error) {
            console.error("Error al exportar:", error);
            alert(`Ocurrió un error al intentar exportar: ${error.message}`);
        }
    }
    
    function obtenerDatosDeTabla(tableHeader, tableBody) {
        const filas = tableBody.querySelectorAll('tr');
        if (filas.length === 0 || (filas.length === 1 && filas[0].querySelector('td')?.colSpan > 1)) {
            return null;
        }
        const headers = Array.from(tableHeader.querySelectorAll('th')).map(th => th.textContent);
        const datos = [headers];
        filas.forEach(fila => {
            const celdas = Array.from(fila.querySelectorAll('td'));
            datos.push(celdas.map(td => td.textContent));
        });
        const colores = Array.from(filas).map(fila => 
            Array.from(fila.classList).find(cls => cls.startsWith('fila-')) || ''
        );
        return { datos, colores };
    }

    function exportarExcelMultiHoja(nombreArchivo) {
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
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify(exportData)
        })
        .then(response => {
            if (!response.ok) throw new Error('Error en la exportación del servidor');
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none'; a.href = url; a.download = `${nombreArchivo}.xlsx`;
            document.body.appendChild(a); a.click();
            window.URL.revokeObjectURL(url); document.body.removeChild(a);
        });
    }
    
    function exportarTablaActualCSV(nombreArchivo) {
        if (typeof XLSX === 'undefined') {
            throw new Error("La librería de exportación a CSV (SheetJS) no está disponible.");
        }
        const tabActiva = document.querySelector('.tablinks.active').id;
        const data = tabActiva === 'tabDetalle' 
            ? obtenerDatosDeTabla(detalleHeader, detalleBody)
            : obtenerDatosDeTabla(document.querySelector('#tablaRetardos thead'), retardosBody);

        if (!data) {
            alert('No hay datos para exportar.');
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
        document.body.removeChild(link);
    }
    
    function exportarTablaActualPDF(nombreArchivo) {
        if (typeof jspdf === 'undefined' || typeof jspdf.jsPDF === 'undefined') {
             throw new Error("La librería de exportación a PDF (jsPDF) no está disponible.");
        }
        
        const tabActiva = document.querySelector('.tablinks.active').id;
        const data = tabActiva === 'tabDetalle' 
            ? obtenerDatosDeTabla(detalleHeader, detalleBody)
            : obtenerDatosDeTabla(document.querySelector('#tablaRetardos thead'), retardosBody);
        
        if (!data) {
            alert('No hay datos para exportar.');
            return;
        }

        const { jsPDF } = window.jspdf;
        const doc = new jsPDF({ orientation: 'landscape' });
        
        const colorMap = {
            'fila-falta': [255, 204, 204], 'fila-retardo-normal': [255, 242, 204],
            'fila-permiso': [212, 237, 218], 'fila-retardo-cumplido': [230, 212, 237],
            'fila-descanso': [155, 89, 182], 'fila-retardo-mayor': [255, 217, 102],
            'fila-salida-anticipada': [248, 203, 173],
        };

        doc.autoTable({
            head: [data.datos[0]],
            body: data.datos.slice(1),
            startY: 20,
            styles: { fontSize: 8 },
            headStyles: { fillColor: [39, 174, 96] },
            didParseCell: function(hookData) {
                if (hookData.section === 'body') {
                    const cssClass = data.colores[hookData.row.index];
                    if (cssClass && colorMap[cssClass]) {
                        hookData.cell.styles.fillColor = colorMap[cssClass];
                        if (cssClass === 'fila-descanso') {
                            hookData.cell.styles.textColor = [255, 255, 255];
                        }
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

    [fechaInicio, fechaFin, sucursalSelect].forEach(el => el.addEventListener("change", cargarDatos));
    buscarEmpleado.addEventListener("input", filtrarYRenderizar);
    tabDetalle.addEventListener("click", switchTab);
    tabRetardos.addEventListener("click", switchTab);
    btnExcel.addEventListener('click', () => exportarA('xlsx'));
    btnCSV.addEventListener('click', () => exportarA('csv'));
    btnPDF.addEventListener('click', () => exportarA('pdf'));

    const today = new Date();
    const unaSemanaAtras = new Date();
    unaSemanaAtras.setDate(today.getDate() - 6);
    
    const formatDate = (date) => date.toISOString().split('T')[0];
    
    fechaInicio.value = formatDate(unaSemanaAtras);
    fechaFin.value = formatDate(today);
    
    tabDetalle.click();
});