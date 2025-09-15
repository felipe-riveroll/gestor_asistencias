document.addEventListener("DOMContentLoaded", function () {
  // Referencias a elementos
  const fechaInicio = document.getElementById("fechaInicio");
  const fechaFin = document.getElementById("fechaFin");
  const buscarEmpleado = document.getElementById("buscarEmpleado");
  const sucursalSelect = document.getElementById("sucursal");
  const detalleBody = document.getElementById("detalleBody");
  const retardosBody = document.getElementById("retardosBody");
  const btnPDF = document.getElementById("btnPDF");
  const btnExcel = document.getElementById("btnExcel");
  const btnCSV = document.getElementById("btnCSV");

  // Tabs
  const tabDetalle = document.getElementById("tabDetalle");
  const tabRetardos = document.getElementById("tabRetardos");
  const sectionDetalle = document.getElementById("Detalle");
  const sectionRetardos = document.getElementById("Retardos");

  // Deshabilitar botones de exportación inicialmente
  btnPDF.disabled = true;
  btnExcel.disabled = true;
  btnCSV.disabled = true;

  // Datos de ejemplo (hardcoded)
  const datosCompletos = {
    "31pte": {
      detalle: [
        {
          idEmpleado: "77",
          nombre: "Amelia Contreras Serrano",
          turno: "COLABORADOR",
          fecha: "2025-05-01",
          dia: "Lunes",
          horasEsperadas: "08:00",
          horasTotales: "07:45",
          checada1: "08:15",
          checada2: "12:00",
          checada3: "13:15",
          checada4: "17:00",
          checada5: "",
          observaciones: "Retardo de 15 minutos",
        },
        {
          idEmpleado: "78",
          nombre: "Juan Pérez López",
          turno: "ADMINISTRATIVO",
          fecha: "2025-05-01",
          dia: "Lunes",
          horasEsperadas: "08:00",
          horasTotales: "08:00",
          checada1: "08:00",
          checada2: "12:00",
          checada3: "13:00",
          checada4: "17:00",
          checada5: "",
          observaciones: "",
        },
      ],
      retardos: [
        {
          idEmpleado: "77",
          nombre: "Amelia Contreras Serrano",
          turno: "COLABORADOR",
          fecha: "2025-05-01",
          dia: "Lunes",
          horaEsperada: "08:00",
          horaReal: "08:15",
          tiempoRetardo: "00:15",
          observaciones: "Llegó tarde",
        },
        {
          idEmpleado: "77",
          nombre: "Amelia Contreras Serrano",
          turno: "COLABORADOR",
          fecha: "2025-05-03",
          dia: "Miércoles",
          horaEsperada: "08:00",
          horaReal: "08:30",
          tiempoRetardo: "00:30",
          observaciones: "Tráfico pesado",
        },
      ],
    },
    villas: {
      detalle: [
        {
          idEmpleado: "101",
          nombre: "María Rodríguez Sánchez",
          turno: "MATUTINO",
          fecha: "2025-05-01",
          dia: "Lunes",
          horasEsperadas: "08:00",
          horasTotales: "08:00",
          checada1: "08:00",
          checada2: "12:00",
          checada3: "13:00",
          checada4: "17:00",
          checada5: "",
          observaciones: "",
        },
      ],
      retardos: [
        {
          idEmpleado: "102",
          nombre: "Carlos Méndez Ruiz",
          turno: "VESPERTINO",
          fecha: "2025-05-02",
          dia: "Martes",
          horaEsperada: "14:00",
          horaReal: "14:25",
          tiempoRetardo: "00:25",
          observaciones: "Retardo justificado",
        },
      ],
    },
    nave: { detalle: [], retardos: [] },
    rioblanco: {
      detalle: [
        {
          idEmpleado: "201",
          nombre: "Laura Gómez Hernández",
          turno: "NOCTURNO",
          fecha: "2025-05-01",
          dia: "Lunes",
          horasEsperadas: "20:00",
          horasTotales: "07:30",
          checada1: "20:30",
          checada2: "00:00",
          checada3: "01:00",
          checada4: "04:00",
          checada5: "",
          observaciones: "Retardo de 30 minutos",
        },
      ],
      retardos: [
        {
          idEmpleado: "201",
          nombre: "Laura Gómez Hernández",
          turno: "NOCTURNO",
          fecha: "2025-05-01",
          dia: "Lunes",
          horaEsperada: "20:00",
          horaReal: "20:30",
          tiempoRetardo: "00:30",
          observaciones: "Primer retardo",
        },
      ],
    },
  };

  // Función para comparar fechas ignorando horas
  function esMismaFechaOEnRango(fechaItem, inicio, fin) {
    const f = new Date(fechaItem.getFullYear(), fechaItem.getMonth(), fechaItem.getDate());
    const start = inicio ? new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate()) : null;
    const end = fin ? new Date(fin.getFullYear(), fin.getMonth(), fin.getDate()) : null;

    if (start && f < start) return false;
    if (end && f > end) return false;
    return true;
  }

  // Pintar tabla detalle
  function pintarTablaDetalle(datos) {
    detalleBody.innerHTML = "";
    if (datos.length === 0) {
      detalleBody.innerHTML =
        '<tr><td colspan="12" style="text-align:center;">No hay registros de checadas para la sucursal y filtro seleccionados.</td></tr>';
      return;
    }
    datos.forEach((registro) => {
      const tr = document.createElement("tr");
      if (registro.observaciones && registro.observaciones.toLowerCase().includes("retardo")) {
        tr.classList.add("retardo-row");
      }
      const campos = [
        "idEmpleado","nombre","turno","fecha","dia",
        "horasEsperadas","horasTotales",
        "checada1","checada2","checada3","checada4","checada5","observaciones"
      ];
      campos.forEach((campo) => {
        const td = document.createElement("td");
        td.textContent = registro[campo] || "";
        tr.appendChild(td);
      });
      detalleBody.appendChild(tr);
    });
  }

  // Pintar tabla retardos
  function pintarTablaRetardos(datos) {
    retardosBody.innerHTML = "";
    if (datos.length === 0) {
      retardosBody.innerHTML =
        '<tr><td colspan="9" style="text-align:center;">No hay registros de retardos para la sucursal y filtro seleccionados.</td></tr>';
      return;
    }
    datos.forEach((registro) => {
      const tr = document.createElement("tr");
      const campos = [
        "idEmpleado","nombre","turno","fecha","dia",
        "horaEsperada","horaReal","tiempoRetardo","observaciones"
      ];
      campos.forEach((campo) => {
        const td = document.createElement("td");
        td.textContent = registro[campo] || "";
        tr.appendChild(td);
      });
      retardosBody.appendChild(tr);
    });
  }

  // Filtrar datos según filtros seleccionados
  function filtrarDatos() {
    const sucursal = sucursalSelect.value;
    const inicio = fechaInicio.value ? new Date(fechaInicio.value) : null;
    const fin = fechaFin.value ? new Date(fechaFin.value) : null;
    const busqueda = buscarEmpleado.value.toLowerCase();

    let datosDetalle = [];
    let datosRetardos = [];

    if (!sucursal) {
      detalleBody.innerHTML = "";
      retardosBody.innerHTML = "";
      btnPDF.disabled = true;
      btnExcel.disabled = true;
      btnCSV.disabled = true;
      return;
    }

    if (sucursal === "all") {
      for (const key in datosCompletos) {
        datosDetalle = datosDetalle.concat(datosCompletos[key].detalle);
        datosRetardos = datosRetardos.concat(datosCompletos[key].retardos);
      }
    } else if (datosCompletos[sucursal]) {
      datosDetalle = datosCompletos[sucursal].detalle;
      datosRetardos = datosCompletos[sucursal].retardos;
    }

    // Filtrar detalle
    datosDetalle = datosDetalle.filter((item) => {
      const fechaItem = new Date(item.fecha);
      const dentroRango = esMismaFechaOEnRango(fechaItem, inicio, fin);
      const textoCompleto = (item.nombre + item.idEmpleado).toLowerCase();
      const incluyeBusqueda = textoCompleto.includes(busqueda);
      return dentroRango && incluyeBusqueda;
    });

    // Filtrar retardos
    datosRetardos = datosRetardos.filter((item) => {
      const fechaItem = new Date(item.fecha);
      const dentroRango = esMismaFechaOEnRango(fechaItem, inicio, fin);
      const textoCompleto = (item.nombre + item.idEmpleado).toLowerCase();
      const incluyeBusqueda = textoCompleto.includes(busqueda);
      const tieneRetardo = item.tiempoRetardo && item.tiempoRetardo !== "00:00";
      return dentroRango && incluyeBusqueda && tieneRetardo;
    });

    pintarTablaDetalle(datosDetalle);
    pintarTablaRetardos(datosRetardos);

    // Habilitar botones de exportación si hay datos
    const hayDatos = datosDetalle.length > 0 || datosRetardos.length > 0;
    btnPDF.disabled = !hayDatos;
    btnExcel.disabled = !hayDatos;
    btnCSV.disabled = !hayDatos;
  }

  // Manejo de pestañas
  function switchTab(selectedTab) {
    // Remover clase active de todos los tabs
    [tabDetalle, tabRetardos].forEach((tab) => {
      tab.classList.remove("active");
      tab.setAttribute("aria-selected", "false");
    });
    
    // Ocultar todos los contenidos
    [sectionDetalle, sectionRetardos].forEach((sec) => {
      sec.classList.remove("active");
      sec.style.display = "none";
    });

    // Activar el tab seleccionado
    selectedTab.classList.add("active");
    selectedTab.setAttribute("aria-selected", "true");

    // Mostrar el contenido correspondiente
    const panelId = selectedTab.id.replace("tab", "");
    const panel = document.getElementById(panelId);
    panel.style.display = "block";
    panel.classList.add("active");

    filtrarDatos(); // refrescar datos al cambiar
  }

  // Funciones de exportación
  function exportarPDF() {
    if (sucursalSelect.value === "") {
      alert("Por favor, selecciona una sucursal primero");
      return;
    }
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation: 'landscape', unit: 'mm' });
    const activeTab = document.querySelector('.tablinks.active').id;
    let title, headers, data;

    if (activeTab === 'tabDetalle') {
      title = 'Reporte de Checadas - Detalle';
      headers = ['ID Empleado','Nombre','Turno','Fecha','Día',
                 'Horas Esperadas','Horas Totales',
                 'Checada 1','Checada 2','Checada 3','Checada 4','Checada 5','Observaciones'];
      data = Array.from(document.querySelectorAll('#detalleBody tr')).map(tr =>
        Array.from(tr.children).map(td => td.textContent));
    } else if (activeTab === 'tabRetardos') {
      title = 'Reporte de Checadas - Retardos';
      headers = ['ID Empleado','Nombre','Turno','Fecha','Día',
                 'Hora Esperada','Hora Real','Retardo','OBS'];
      data = Array.from(document.querySelectorAll('#retardosBody tr')).map(tr =>
        Array.from(tr.children).map(td => td.textContent));
    }

    doc.text(title, 14, 10);
    doc.autoTable({ 
      head: [headers], 
      body: data, 
      startY: 20, 
      styles: { fontSize: 8, cellPadding: 2 },
      columnStyles: {
        0: { cellWidth: 15 },
        1: { cellWidth: 30 },
        2: { cellWidth: 20 },
        3: { cellWidth: 20 },
        4: { cellWidth: 15 },
        5: { cellWidth: 20 },
        6: { cellWidth: 20 },
        7: { cellWidth: 15 },
        8: { cellWidth: 15 },
        9: { cellWidth: 15 },
        10: { cellWidth: 15 },
        11: { cellWidth: 30 }
      }
    });
    doc.save('reporte_checadas.pdf');
  }

  function exportarExcel() {
    if (sucursalSelect.value === "") {
      alert("Por favor, selecciona una sucursal primero");
      return;
    }
    const activeTab = document.querySelector('.tablinks.active').id;
    let data = [];
    let fileName = 'reporte_checadas.xlsx';

    if (activeTab === 'tabDetalle') {
      data.push(['ID Empleado','Nombre','Turno','Fecha','Día',
                 'Horas Esperadas','Horas Totales',
                 'Checada 1','Checada 2','Checada 3','Checada 4','Checada 5','Observaciones']);
      document.querySelectorAll('#detalleBody tr').forEach(tr =>
        data.push(Array.from(tr.children).map(td => td.textContent)));
      fileName = 'reporte_detalle.xlsx';
    } else if (activeTab === 'tabRetardos') {
      data.push(['ID Empleado','Nombre','Turno','Fecha','Día',
                 'Hora Esperada','Hora Real','Retardo','OBS']);
      document.querySelectorAll('#retardosBody tr').forEach(tr =>
        data.push(Array.from(tr.children).map(td => td.textContent)));
      fileName = 'reporte_retardos.xlsx';
    }

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.aoa_to_sheet(data);
    XLSX.utils.book_append_sheet(wb, ws, 'Reporte');
    XLSX.writeFile(wb, fileName);
  }

  function exportarCSV() {
    if (sucursalSelect.value === "") {
      alert("Por favor, selecciona una sucursal primero");
      return;
    }
    const activeTab = document.querySelector('.tablinks.active').id;
    let csvContent = '';
    let fileName = 'reporte_checadas.csv';

    if (activeTab === 'tabDetalle') {
      csvContent += ['ID Empleado','Nombre','Turno','Fecha','Día',
                     'Horas Esperadas','Horas Totales',
                     'Checada 1','Checada 2','Checada 3','Checada 4','Checada 5','Observaciones'].join(',') + '\r\n';
      document.querySelectorAll('#detalleBody tr').forEach(tr => {
        csvContent += Array.from(tr.children).map(td =>
          `"${td.textContent.replace(/"/g, '""')}"`).join(',') + '\r\n';
      });
      fileName = 'reporte_detalle.csv';
    } else if (activeTab === 'tabRetardos') {
      csvContent += ['ID Empleado','Nombre','Turno','Fecha','Día',
                     'Hora Esperada','Hora Real','Retardo','OBS'].join(',') + '\r\n';
      document.querySelectorAll('#retardosBody tr').forEach(tr => {
        csvContent += Array.from(tr.children).map(td =>
          `"${td.textContent.replace(/"/g, '""')}"`).join(',') + '\r\n';
      });
      fileName = 'reporte_retardos.csv';
    }

    const encodedUri = encodeURI('data:text/csv;charset=utf-8,' + csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // Event listeners
  tabDetalle.addEventListener("click", () => switchTab(tabDetalle));
  tabRetardos.addEventListener("click", () => switchTab(tabRetardos));
  
  fechaInicio.addEventListener("change", filtrarDatos);
  fechaFin.addEventListener("change", filtrarDatos);
  buscarEmpleado.addEventListener("input", filtrarDatos);
  sucursalSelect.addEventListener("change", filtrarDatos);
  
  btnPDF.addEventListener("click", exportarPDF);
  btnExcel.addEventListener("click", exportarExcel);
  btnCSV.addEventListener("click", exportarCSV);

  // Inicialización
  // Activar detalle por defecto
  switchTab(tabDetalle);
});