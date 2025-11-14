document.addEventListener("DOMContentLoaded", () => {
  // --- Elementos del DOM: Modal AGREGAR ---
  const modal = document.getElementById("employeeModal");
  const form = document.getElementById("employeeForm");
  const btnAdd = document.getElementById("btnAdd"); // Botón flotante '+'
  const btnCancel = document.querySelector("#employeeModal .btn-cancel"); // Cancelar de modal AGREGAR
  const sucursalSelect = document.getElementById("sucursal");
  const horarioSelect = document.getElementById("horario");
  const btnAgregar = document.getElementById("agregarHorario");
  const horariosAgregados = document.getElementById("horariosAgregados");

  // --- Elementos del DOM: Modal EDITAR ---
  const editModal = document.getElementById("editEmployeeModal");
  const editForm = document.getElementById("editEmployeeForm");
  const sucursalSelectEdit = document.getElementById("sucursalEdit");
  const horarioSelectEdit = document.getElementById("horarioEdit");
  const btnAgregarEdit = document.getElementById("agregarHorarioEdit");
  const horariosAgregadosEdit = document.getElementById("horariosAgregadosEdit");

  // --- Elementos del DOM: Comunes ---
  const closeButtons = document.querySelectorAll(".close");
  const searchInput = document.getElementById("searchInput");
  const tableBody = document.getElementById("employeeTableBody");

  // --- Elementos del DOM: Modal de Horarios (el pequeño) ---
  const scheduleModal = document.getElementById("scheduleModal");
  const btnAddSchedule = document.getElementById("btnAddSchedule");
  const scheduleForm = document.getElementById("scheduleForm");
  const cancelAddSchedule = document.getElementById("cancelAddSchedule");

  // =================================================================
  // LÓGICA DE BÚSQUEDA EN TABLA
  // =================================================================
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

  // =================================================================
  // ABRIR MODAL DE AGREGAR (Botón flotante '+')
  // =================================================================
  btnAdd.addEventListener("click", () => {
    modal.style.display = "flex";
    form.reset(); // Limpia el formulario
    // Limpia horarios agregados
    horariosAgregados.innerHTML = `<div class="empty-schedule">No hay horarios agregados</div>`;
    document.getElementById("modalTitle").innerText = "Agregar Empleado";
  });

  // =================================================================
  // ABRIR MODAL DE EDICIÓN (Botones verdes en la tabla)
  // =================================================================
  tableBody.addEventListener("click", (e) => {
    // Busca el botón de editar más cercano al que se hizo clic
    const editButton = e.target.closest(".btn-editar");

    // Si se hizo clic en un botón de editar
    if (editButton) {
      e.preventDefault(); // Previene que el link <a> navegue
      
      const data = editButton.dataset; // Lee todos los 'data-' atributos

      // 1. Rellena el formulario de EDICIÓN con los datos de la tabla
      document.getElementById('employeeIdEdit').value = data.id;
      document.getElementById('employeeIndexDisplay').value = data.id; 
      document.getElementById('codigoFrappeEdit').value = data.frappe;
      document.getElementById('codigoChecadorEdit').value = data.checador;
      document.getElementById('nombreEdit').value = data.nombre;
      document.getElementById('primerApellidoEdit').value = data.paterno;
      document.getElementById('segundoApellidoEdit').value = data.materno;
      document.getElementById('emailEdit').value = data.email;
      // --- ¡AÑADE ESTA LÍNEA! ---
      // Esto le pone la URL correcta al formulario (ej: /empleados/editar/80/)
      editForm.action = `/empleados/editar/${data.id}/`;
      // Limpia horarios previos
      horariosAgregadosEdit.innerHTML = `<div class="empty-schedule">Cargando horarios...</div>`;

      // 2. Llama a las APIs para rellenar los <select> del modal de EDICIÓN
      cargarSucursales(sucursalSelectEdit); // Pasa el <select> de EDICIÓN
      cargarHorarios(horarioSelectEdit);   // Pasa el <select> de EDICIÓN
      
      // ----------------------------------------------------------------
      // ¡¡AQUÍ ESTÁ EL CAMBIO #1!!
      // Se activa la llamada a la nueva función para cargar horarios guardados
      // ----------------------------------------------------------------
      cargarHorariosAsignados(data.id); 

      // 4. Muestra el modal de EDICIÓN
      editModal.style.display = "flex";
    }
  });


  // =================================================================
  // LÓGICA PARA AGREGAR ETIQUETAS DE HORARIO
  // =================================================================

  // --- Lógica para el modal de AGREGAR ---
  if (btnAgregar) {
    btnAgregar.addEventListener("click", function () {
      // Usamos 'employeeModal' como contexto para 'querySelectorAll'
      agregarEtiquetaDeHorario(modal, sucursalSelect, horarioSelect, horariosAgregados);
    });
  }

  // --- Lógica para el modal de EDITAR ---
  if (btnAgregarEdit) {
    btnAgregarEdit.addEventListener("click", function () {
      // Usamos 'editModal' como contexto para 'querySelectorAll'
      agregarEtiquetaDeHorario(editModal, sucursalSelectEdit, horarioSelectEdit, horariosAgregadosEdit);
    });
  }

  /**
   * Función genérica para crear etiquetas de horario.
   */
  function agregarEtiquetaDeHorario(modalContext, sucursalEl, horarioEl, containerEl) {
    const sucursalId = sucursalEl.value;
    const sucursalText = sucursalEl.options[sucursalEl.selectedIndex]?.text;
    const horarioId = horarioEl.value;
    const horarioText = horarioEl.options[horarioEl.selectedIndex]?.text;

    const checkboxes = Array.from(
      modalContext.querySelectorAll(".day-checkbox:checked")
    );

    const diasIds = checkboxes.map((cb) => cb.dataset.id);
    const diasNombres = checkboxes.map(
      (cb) => modalContext.querySelector(`label[for="${cb.id}"]`).innerText
    );

    // Validar
    if (!sucursalId || !horarioId || diasIds.length === 0) {
      alert("Debe seleccionar sucursal, horario y día(s)");
      return;
    }

    //Validar duplicados
    const etiquetas = containerEl.querySelectorAll(".schedule-label");
    for (let etiqueta of etiquetas) {
      const existingDias = etiqueta
        .querySelector('input[name="dias[]"]')
        .value.split(",");

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
      const currentEtiquetas = containerEl.querySelectorAll(".schedule-label");
      if (currentEtiquetas.length === 0) {
        containerEl.innerHTML = `<div class="empty-schedule">No hay horarios agregados</div>`;
      }
    });

    // Quitar el texto vacío inicial
    const empty = containerEl.querySelector(".empty-schedule");
    if (empty) empty.remove();

    containerEl.appendChild(div);

    // Limpiar campos
    checkboxes.forEach(cb => cb.checked = false);
    //sucursalEl.value = "";
    //horarioEl.value = "";
  }

  // =================================================================
  // VALIDACIÓN AL GUARDAR (SUBMIT)
  // =================================================================
  
  // --- Validar formulario de AGREGAR ---
  form.addEventListener("submit", function (e) {
    const horarios = horariosAgregados.querySelectorAll(".schedule-label");
    if (horarios.length === 0) {
      e.preventDefault(); // Evita que el formulario se envíe
      alert("⚠️ Debe asignar al menos un horario antes de guardar.");
      return false;
    }
  });

  // --- Validar formulario de EDITAR ---
  if (editForm) {
    editForm.addEventListener("submit", function (e) {
      const horarios = horariosAgregadosEdit.querySelectorAll(".schedule-label");
      if (horarios.length === 0) {
        e.preventDefault(); // Evita que el formulario se envíe
        alert("⚠️ Debe asignar al menos un horario antes de guardar.");
        return false;
      }
    });
  }


  // =================================================================
  // LÓGICA PARA CERRAR MODALES
  // =================================================================
  closeButtons.forEach((btn) => {
    btn.addEventListener("click", function () {
      const modalToClose = this.closest(".modal");
      modalToClose.style.display = "none";
    });
  });

  if (btnCancel) {
      btnCancel.addEventListener("click", () => (modal.style.display = "none"));
  }
  const btnCancelEdit = document.querySelector("#editEmployeeModal .btn-cancel");
  if (btnCancelEdit) {
      btnCancelEdit.addEventListener("click", () => (editModal.style.display = "none"));
  }


  window.addEventListener("click", (e) => {
    if (e.target.classList.contains("modal")) {
      e.target.style.display = "none";
    }
  });

  // =================================================================
  // MODAL PEQUEÑO DE "AGREGAR HORARIO"
  // =================================================================
  if (btnAddSchedule) {
      btnAddSchedule.addEventListener("click", function (e) {
        e.preventDefault();
        scheduleModal.style.display = "flex";
        scheduleForm.reset();
        document.querySelector(
          'input[name="cruzaNoche"][value="si"]'
        ).checked = true;
        document.getElementById("horaEntrada").focus();
      });
  }

  if (cancelAddSchedule) {
      cancelAddSchedule.addEventListener("click", () => {
        scheduleModal.style.display = "none";
      });
  }


  // =================================================================
  // FUNCIONES DE API (FETCH) PARA RELLENAR SELECTS
  // =================================================================
  
  /**
   * Pide la lista de sucursales a la API y las pone en el <select> que le pases.
   */
  async function cargarSucursales(selectElement) {
    if (!selectElement) return;

    try {
       const response = await fetch('/api/lista_sucursales/'); // ¡URL de tu API!
      if (!response.ok) throw new Error('Error al cargar sucursales');
      
      const sucursales = await response.json();

      selectElement.innerHTML = '<option value="" disabled selected>Seleccione...</option>';

      sucursales.forEach(sucursal => {
        const option = document.createElement('option');
        option.value = sucursal.id;
        option.textContent = sucursal.nombre;
        selectElement.appendChild(option);
      });

    } catch (error) {
      console.error('Error en cargarSucursales:', error);
    }
  }

  /**
   * Pide la lista de horarios a la API y las pone en el <select> que le pases.
   */
  async function cargarHorarios(selectElement) {
    if (!selectElement) return;

    try {
      const response = await fetch('/api/lista_horarios/'); // ¡URL de tu API!
      if (!response.ok) throw new Error('Error al cargar horarios');
      
      const horarios = await response.json();

      selectElement.innerHTML = '<option value="" disabled selected>Seleccione...</option>';

      horarios.forEach(horario => {
        const option = document.createElement('option');
        option.value = horario.id;
        option.textContent = horario.texto; // ej: "Tiempo Completo (9-6)"
        selectElement.appendChild(option);
      });

    } catch (error) {
      console.error('Error en cargarHorarios:', error);
    }
  }

 // ----------------------------------------------------------------
 // ¡¡AQUÍ ESTÁ EL CAMBIO #2!!
 // Se agrega la nueva función para cargar los horarios guardados.
 // ----------------------------------------------------------------
 /**
   * Pide los horarios ASIGNADOS de un empleado y los dibuja en el modal.
   * @param {string} empleadoId - El ID del empleado
   */
  async function cargarHorariosAsignados(empleadoId) {
    const containerEl = document.getElementById('horariosAgregadosEdit');
    containerEl.innerHTML = ''; // Limpia el contenedor

    try {
        // Esta es la nueva URL de API que debes crear en Django
      const response = await fetch(`/api/empleado/${empleadoId}/horarios/`);
      if (!response.ok) throw new Error('Error al cargar horarios asignados');
      
      const horarios = await response.json();

      if (horarios.length === 0) {
        containerEl.innerHTML = `<div class="empty-schedule">No hay horarios agregados</div>`;
        return;
      }

      // Dibuja cada etiqueta de horario
      horarios.forEach(h => {
        const div = document.createElement("div");
        div.classList.add("schedule-label");
        
        // Recreamos la misma estructura HTML que crea 'agregarEtiquetaDeHorario'
        // Asegúrate de que tu API devuelva estos campos:
        // h.sucursal_text, h.dias_nombres, h.horario_text,
        // h.sucursal_id, h.horario_id, h.dias_ids (como array)
        div.innerHTML = `
          <span class="tag-sucursal">${h.sucursal_text}</span>
          <span class="tag-dia">${h.dias_nombres}</span>
          <span class="tag-horas">${h.horario_text}</span>
          <button type="button" class="delete-btn"><i class="fas fa-times"></i></button>

          <input type="hidden" name="sucursales[]" value="${h.sucursal_id}">
          <input type="hidden" name="horarios[]" value="${h.horario_id}">
          <input type="hidden" name="dias[]" value="${h.dias_ids.join(",")}">
        `;
        
        // Botón eliminar (importante para que se puedan borrar)
        div.querySelector(".delete-btn").addEventListener("click", function () {
          div.remove();
          const currentEtiquetas = containerEl.querySelectorAll(".schedule-label");
          if (currentEtiquetas.length === 0) {
            containerEl.innerHTML = `<div class="empty-schedule">No hay horarios agregados</div>`;
          }
        });

        containerEl.appendChild(div);
      });

    } catch (error) {
      console.error('Error en cargarHorariosAsignados:', error);
      containerEl.innerHTML = `<div class="empty-schedule" style="color: red;">Error al cargar horarios</div>`;
    }
  }

});