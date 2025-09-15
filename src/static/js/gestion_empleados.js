document.addEventListener("DOMContentLoaded", () => {
  // Elementos del DOM
  const modal = document.getElementById("employeeModal");
  const closeButtons = document.querySelectorAll(".close");
  const btnAdd = document.getElementById("btnAdd");
  const btnCancel = document.querySelector(".btn-cancel");
  const form = document.getElementById("employeeForm");
  const btnImport = document.getElementById("btnImport");
  const btnExportExcel = document.getElementById("btnExportExcel");
  const btnExportPDF = document.getElementById("btnExportPDF");

  // Elementos para el modal de horarios
  const scheduleModal = document.getElementById("scheduleModal");
  const btnAddSchedule = document.getElementById("btnAddSchedule");
  const scheduleForm = document.getElementById("scheduleForm");
  const cancelAddSchedule = document.getElementById("cancelAddSchedule");

  //Elementos buscar empleados
  const searchInput = document.getElementById("searchInput");
  const tableBody = document.getElementById("employeeTableBody");
  //Elementos para los horarios
  const btnAgregar = document.getElementById("agregarHorario");
  const horariosAgregados = document.getElementById("horariosAgregados");
  const sucursalSelect = document.getElementById("sucursal");
  const horarioSelect = document.getElementById("horario");

  // Datos
  let employees = [];

  //Buscar Empleados
  searchInput.addEventListener("keyup", function () {
    const filter = searchInput.value.toLowerCase();
    const rows = tableBody.getElementsByTagName("tr");

    for (let i = 0; i < rows.length; i++) {
      const cells = rows[i].getElementsByTagName("td");
      let match = false;

      for (let j = 0; j < cells.length; j++) {
        if (cells[j]) {
          const text = cells[j].textContent || cells[j].innerText;
          if (text.toLowerCase().indexOf(filter) > -1) {
            match = true;
            break;
          }
        }
      }

      rows[i].style.display = match ? "" : "none";
    }
  });

  // Eventos para el modal principal de empleados
  btnAdd.addEventListener("click", () => {
    editIndex = null;
    modal.style.display = "flex";
    form.reset();
    document.getElementById("modalTitle").innerText = "Agregar Empleado";
  });

  //Evento mostrar horarios seleccionados
  btnAgregar.addEventListener("click", function () {
    const sucursalId = sucursalSelect.value;
    const sucursalText =
      sucursalSelect.options[sucursalSelect.selectedIndex]?.text;
    const horarioId = horarioSelect.value;
    const horarioText =
      horarioSelect.options[horarioSelect.selectedIndex]?.text;
    const diasSeleccionados = Array.from(
      document.querySelectorAll(".day-checkbox:checked")
    ).map((cb) => cb.value);

    // Validar
    if (!sucursalId || !horarioId || diasSeleccionados === 0) {
      alert("Debe seleccionar sucursal, horario y día(s)");
      return;
    }

    // Crear etiqueta visual
    const div = document.createElement("div");
    div.classList.add("schedule-label");
    div.innerHTML = `
  <span class="tag-sucursal">${sucursalText}</span>
  <span class="tag-dia">${diasSeleccionados.join(", ")}</span>
  <span class="tag-horas">${horarioText}</span>
  <button type="button" class="delete-btn"><i class="fas fa-times"></i></button>
  <input type="hidden" name="sucursales[]" value="${sucursalId}">
  <input type="hidden" name="horarios[]" value="${horarioId}">
  <input type="hidden" name="dias[]" value="${diasSeleccionados.join(",")}">
`;

    // Botón eliminar
    div.querySelector(".delete-btn").addEventListener("click", function () {
      div.remove();
      if (horariosAgregados.children.length === 0) {
        horariosAgregados.innerHTML = `<div class="empty-schedule">No hay horarios agregados</div>`;
      }
    });

    // Quitar el texto vacío inicial
    const empty = horariosAgregados.querySelector(".empty-schedule");
    if (empty) empty.remove();

    horariosAgregados.appendChild(div);
  });

  // Cerrar modales
  closeButtons.forEach((btn) => {
    btn.addEventListener("click", function () {
      const modalToClose = this.closest(".modal");
      modalToClose.style.display = "none";
    });
  });

  btnCancel.addEventListener("click", () => (modal.style.display = "none"));

  window.addEventListener("click", (e) => {
    if (e.target.classList.contains("modal")) {
      e.target.style.display = "none";
    }
  });

  // Evento para abrir modal de horarios
  btnAddSchedule.addEventListener("click", function (e) {
    e.preventDefault();
    scheduleModal.style.display = "flex";
    scheduleForm.reset();
    document.querySelector(
      'input[name="cruzaNoche"][value="si"]'
    ).checked = true;
    document.getElementById("horaEntrada").focus();
  });

  // Botón cancelar del modal de horarios
  cancelAddSchedule.addEventListener("click", () => {
    scheduleModal.style.display = "none";
  });

  // Botón importar desde Excel
  btnImport.addEventListener("click", () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".xlsx,.xls";
    input.onchange = (e) => {
      const file = e.target.files[0];
      const reader = new FileReader();
      reader.onload = (ev) => {
        const data = ev.target.result;
        const workbook = XLSX.read(data, { type: "binary" });
        const sheetName = workbook.SheetNames[0];
        const sheet = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName]);

        sheet.forEach((row) => {
          employees.push({
            id: Date.now().toString(),
            codigoFrappe: row["Código Frappe"] || "",
            codigoChecador: row["Código Checador"] || "",
            nombre: row["Nombre"] || "",
            primerApellido: row["Primer Apellido"] || "",
            segundoApellido: row["Segundo Apellido"] || "",
            email: row["Email"] || "",
            sucursal: row["Sucursal"] || "",
            horario: row["Horario"] || "",
          });
        });
        renderTable();
      };
      reader.readAsBinaryString(file);
    };
    input.click();
  });

  // Botón exportar a Excel
  btnExportExcel.addEventListener("click", exportToExcel);

  // Botón exportar a PDF
  btnExportPDF.addEventListener("click", exportToPDF);

  // Inicialización
  renderTable();
  autoRefreshTable();
});