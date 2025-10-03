document.addEventListener("DOMContentLoaded", () => {
  // Elementos del DOM
  const modal = document.getElementById("employeeModal");
  const closeButtons = document.querySelectorAll(".close");
  const btnAdd = document.getElementById("btnAdd");
  const btnCancel = document.querySelector(".btn-cancel");
  const btnGuardar = document.getElementById("employeeForm");
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

    // Obtener los checkboxes seleccionados
    const checkboxes = Array.from(
      document.querySelectorAll(".day-checkbox:checked")
    );

    // Extraer IDs y nombres
    const diasIds = checkboxes.map((cb) => cb.dataset.id);
    const diasNombres = checkboxes.map(
      (cb) => document.querySelector(`label[for="${cb.id}"]`).innerText
    );

    // Validar
    if (!sucursalId || !horarioId || diasIds.length === 0) {
      alert("Debe seleccionar sucursal, horario y día(s)");
      return;
    }

    //Validar duplicados
    const etiquetas = document.querySelectorAll(".schedule-label");
    for (let etiqueta of etiquetas) {
      const existingDias = etiqueta
        .querySelector('input[name="dias[]"]')
        .value.split(",");

      // Si algún día seleccionado ya existe en otra etiqueta
      if (diasIds.some((d) => existingDias.includes(d))) {
        alert("⚠️ Uno o más días ya están asignados en otro horario.");
        return;
      }
    }

    // Crear etiqueta visual
    const div = document.createElement("div");
    div.classList.add("schedule-label");
    div.innerHTML = `
    <span class="tag-sucursal">${sucursalText}</span>
    <span class="tag-dia">${diasNombres.join(", ")}</span>
    <span class="tag-horas">${horarioText}</span>
    <button type="button" class="delete-btn"><i class="fas fa-times"></i></button>

    <input type="hidden" name="sucursales[]" value="${sucursalId}">
    <input type="hidden" name="horarios[]" value="${horarioId}">
    <input type="hidden" name="dias[]" value="${diasIds.join(",")}">
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

  btnGuardar.addEventListener("submit", function (e) {
      // Contar las etiquetas de horarios agregados
      const horarios = document.querySelectorAll(".schedule-label");

      if (horarios.length === 0) {
        e.preventDefault(); // Evita que el formulario se envíe
        alert(
          "⚠️ Debe asignar un horario antes de guardar el empleado."
        );
        return false;
      }
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
});
