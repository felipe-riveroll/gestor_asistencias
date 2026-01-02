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
    const tabDetalle = document.getElementById("tabDetalle");
    const tabRetardos = document.getElementById("tabRetardos");
    const sectionDetalle = document.getElementById("Detalle");
    const sectionRetardos = document.getElementById("Retardos");

    let todasLasAsistencias = [];

    // ==========================================================
    // FUNCIONES DE UTILIDAD PARA TIEMPO
    // ==========================================================

    function duracionASegundos(duracion) {
        if (typeof duracion !== 'string' || !duracion || duracion === '00:00:00' || duracion === '-') return 0;
        
        const partes = duracion.split(':');
        if (partes.length !== 3) return 0;
        
        const h = parseInt(partes[0]) || 0;
        const m = parseInt(partes[1]) || 0;
        const s = parseInt(partes[2]) || 0;
        
        return (h * 3600) + (m * 60) + s;
    }

    function segundosADuracion(segundos) {
        let totalSegundos = Number(segundos) || 0;
        if (totalSegundos < 0) totalSegundos = 0;
        
        const h = Math.floor(totalSegundos / 3600);
        const segundosRestantes = totalSegundos % 3600;
        const m = Math.floor(segundosRestantes / 60);
        const s = segundosRestantes % 60;

        const minutosStr = m.toString().padStart(2, '0');
        const segundosStr = s.toString().padStart(2, '0');
        
        return `${h}:${minutosStr}:${segundosStr}`;
    }

    function calcularTotalesPorEmpleado(datos) {
        const totales = {};

        datos.forEach(d => {
            const id = d.employee;
            const nombre = d.Nombre;
            const horasTrabajadasSegundos = duracionASegundos(d.duration);
            
            let horasEsperadasSegundos = Number(d.horas_esperadas);
            if (isNaN(horasEsperadasSegundos) || horasEsperadasSegundos === 0) {
                horasEsperadasSegundos = duracionASegundos(String(d.horas_esperadas));
            }

            if (!totales[id]) {
                totales[id] = {
                    Nombre: nombre,
                    conteoDias: 0,
                    totalHorasSegundos: 0,
                    totalEsperadasSegundos: 0
                };
            }

            totales[id].totalHorasSegundos += horasTrabajadasSegundos;
            totales[id].totalEsperadasSegundos += horasEsperadasSegundos;

            if (d.observacion_incidencia !== 'Descanso' && d.observacion_incidencia !== 'Falta') {
                 totales[id].conteoDias += 1;
            }
        });

        for (const id in totales) {
            totales[id].totalHorasTotales = segundosADuracion(totales[id].totalHorasSegundos);
            totales[id].totalHorasEsperadas = segundosADuracion(totales[id].totalEsperadasSegundos);
        }

        return totales;
    }

    // ==========================================================
    // LÓGICA PRINCIPAL DEL REPORTE
    // ==========================================================

    async function cargarDatos() {
        detalleBody.innerHTML = '<tr><td colspan="10" style="text-align: center;">Cargando...</td></tr>';
        retardosBody.innerHTML = '<tr><td colspan="8" style="text-align: center;">Cargando...</td></tr>';
        [btnPDF, btnExcel].forEach(btn => {
            if(btn) btn.disabled = true;
        });

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
        let datosFiltrados = todasLasAsistencias.filter(item => {
            if (!busqueda) return true;
            const nombre = (item.Nombre || '').toLowerCase();
            const id = (item.employee || '').toString().toLowerCase();
            return nombre.includes(busqueda) || id.includes(busqueda);
        });
        
        datosFiltrados.sort((a, b) => (a.employee > b.employee) ? 1 : ((b.employee > a.employee) ? -1 : 0));
        
        const datosRetardos = datosFiltrados.filter(item => 
            item.observacion_incidencia === 'Retardo Normal' || item.observacion_incidencia === 'Retardo Mayor'
        );
        
        const totalesEmpleados = calcularTotalesPorEmpleado(datosFiltrados);
        
        pintarTablaDetalle(datosFiltrados, totalesEmpleados); 
        pintarTablaRetardos(datosRetardos);
        const hayDatos = datosFiltrados.length > 0;
        [btnPDF, btnExcel].forEach(btn => {
            if(btn) btn.disabled = !hayDatos;
        });
    }

    function pintarTablaDetalle(datos, totalesEmpleados) {
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
        
        let headersHTML = `<th>ID Empleado</th><th>Nombre</th><th>Turno</th><th>Fecha</th><th>Día</th><th>Horas Esperadas</th><th>Horas Totales</th>`;
        for (let i = 1; i <= maxChecadas; i++) headersHTML += `<th>Checado ${i}</th>`;
        headersHTML += `<th>Observaciones</th>`;
        detalleHeader.innerHTML = `<tr>${headersHTML}</tr>`;

        let empleadoActual = null;
        const totalChecadasColspan = maxChecadas + 1; 
        
        datos.forEach(d => {
            if (empleadoActual !== null && empleadoActual !== d.employee) {
                const total = totalesEmpleados[empleadoActual];
                const trTotal = document.createElement("tr");
                trTotal.className = 'fila-totales';
                trTotal.innerHTML = `
                    <td colspan="1">${empleadoActual}</td>
                    <td colspan="1">${total.Nombre}</td>
                    <td colspan="1">Totales</td>
                    <td colspan="1">${total.conteoDias}</td>
                    <td colspan="1"></td>
                    <td colspan="1">${total.totalHorasEsperadas}</td> 
                    <td colspan="1">${total.totalHorasTotales}</td>
                    <td colspan="${totalChecadasColspan}"></td>
                `;
                detalleBody.appendChild(trTotal);
            }
            
            const tr = document.createElement("tr");
            const observacion = d.observacion_incidencia || 'OK';
            
            // --- AQUÍ ESTÁ LA LÓGICA DE COLORES CORREGIDA ---
            switch (observacion) {
                case 'OK': 
                    tr.className = 'fila-ok'; 
                    break;
                case 'Retardo Normal': 
                    tr.className = 'fila-retardo-normal'; 
                    break;
                case 'Falta': 
                    tr.className = 'fila-falta'; 
                    break;
                case 'Descanso': 
                    tr.className = 'fila-descanso'; 
                    break;
                
                // NUEVO: Caso para Festivos
                case 'Festivo':
                case 'Día Festivo':
                    tr.className = 'fila-festivo'; 
                    break;

                case 'Permiso': 
                    tr.className = 'fila-permiso'; 
                    break;
                case 'Retardo Mayor': 
                    tr.className = 'fila-retardo-mayor'; 
                    break;
                case 'Salida Anticipada': 
                    tr.className = 'fila-salida-anticipada'; 
                    break;
                case 'Cumplió con horas': 
                    tr.className = 'fila-retardo-cumplido'; 
                    break;
                default:
                    // Si contiene la palabra "Festivo" aunque no sea exacta
                    if (observacion.includes('Festivo')) {
                        tr.className = 'fila-festivo';
                    }
                    break;
            }

            let horasEsperadasDisplay = d.horas_esperadas || '00:00:00';
            if (!isNaN(Number(d.horas_esperadas)) && Number(d.horas_esperadas) > 0) {
                horasEsperadasDisplay = segundosADuracion(d.horas_esperadas);
            } else if (d.horas_esperadas && d.horas_esperadas.includes(':')) {
                horasEsperadasDisplay = d.horas_esperadas;
            } else {
                horasEsperadasDisplay = '-'; 
            }
            
            let rowHTML = `<td>${d.employee||''}</td><td>${d.Nombre||''}</td><td>${d.Turno||'-'}</td><td>${d.dia||''}</td><td>${d.dia_semana||''}</td><td>${horasEsperadasDisplay}</td><td>${d.duration||'00:00:00'}</td>`;
            for (let i = 1; i <= maxChecadas; i++) rowHTML += `<td>${d['checado_'+i]||'-'}</td>`;
            rowHTML += `<td>${observacion}</td>`;
            tr.innerHTML = rowHTML;
            detalleBody.appendChild(tr);

            empleadoActual = d.employee;
        });

        if (empleadoActual !== null) {
            const total = totalesEmpleados[empleadoActual];
            const trTotal = document.createElement("tr");
            trTotal.className = 'fila-totales';
            trTotal.innerHTML = `
                <td colspan="1">${empleadoActual}</td>
                <td colspan="1">${total.Nombre}</td>
                <td colspan="1">Totales</td>
                <td colspan="1">${total.conteoDias}</td>
                <td colspan="1"></td>
                <td colspan="1">${total.totalHorasEsperadas}</td> 
                <td colspan="1">${total.totalHorasTotales}</td>
                <td colspan="${totalChecadasColspan}"></td>
            `;
            detalleBody.appendChild(trTotal);
        }
    }
    
    function pintarTablaRetardos(datos) {
        retardosBody.innerHTML = "";
        if (datos.length === 0) {
            retardosBody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No hay retardos.</td></tr>';
            return;
        }
        datos.forEach(d => {
            const tr = document.createElement("tr");
            const observacion = d.observacion_incidencia || '';

            if (observacion === 'Retardo Normal') {
                tr.className = 'fila-retardo-normal'; 
            } else if (observacion === 'Retardo Mayor') {
                tr.className = 'fila-falta'; 
            }

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
        
        const filasDatos = Array.from(filas);

        const datos = [headers];
        filasDatos.forEach(fila => {
            const celdas = Array.from(fila.querySelectorAll('td'));
            datos.push(celdas.map(td => td.textContent));
        });
        const colores = Array.from(filasDatos).map(fila => 
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
        
        // --- MAPA DE COLORES ACTUALIZADO ---
        const colorMap = {
            'fila-retardo-normal': [255, 255, 0],   // Amarillo
            'fila-falta':          [255, 0, 0],     // Rojo
            'fila-retardo-mayor':  [255, 0, 0],     // Rojo
            'fila-permiso':        [146, 208, 80],  // Verde
            'fila-txt-extra':      [0, 176, 240],   // Azul
            'fila-tomo-txt':       [56, 87, 35],    // Verde Oscuro
            'fila-descanso':       [112, 48, 160],  // Morado Oscuro
            'fila-festivo':        [142, 68, 173],  // Morado CORRECTO (#8E44AD)
            'fila-totales':        [221, 235, 247]  // Gris Azulado
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
                        
                        // --- AQUÍ HACEMOS QUE EL TEXTO SEA BLANCO EN FESTIVOS Y DESCANSOS ---
                        if (cssClass === 'fila-descanso' || cssClass === 'fila-festivo') {
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

    if (buscarEmpleado) {
        buscarEmpleado.addEventListener("input", filtrarYRenderizar);
    }
    
    [fechaInicio, fechaFin, sucursalSelect].forEach(el => {
        if (el) el.addEventListener("change", cargarDatos);
    });

    if (tabDetalle) tabDetalle.addEventListener("click", switchTab);
    if (tabRetardos) tabRetardos.addEventListener("click", switchTab);
    
    if (btnExcel) btnExcel.addEventListener('click', () => exportarA('xlsx'));
    if (btnPDF) btnPDF.addEventListener('click', () => exportarA('pdf'));
    
    const today = new Date();
    const oneMonthAgo = new Date(); 
    oneMonthAgo.setMonth(today.getMonth() - 1);
    
    const formatDate = (date) => {
        const d = new Date(date);
        d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
        return d.toISOString().split('T')[0];
    };
    
    if(fechaInicio) fechaInicio.value = formatDate(oneMonthAgo);
    if(fechaFin) fechaFin.value = formatDate(today);
    
    if(sucursalSelect) {
        sucursalSelect.value = "Todas"; 
    }
    
    if(tabDetalle) tabDetalle.click();

    cargarDatos();
});