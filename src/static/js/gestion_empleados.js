document.addEventListener("DOMContentLoaded", () => {
    // --- Elementos del DOM: Modal AGREGAR (Formulario principal) ---
    const modal = document.getElementById("employeeModal");
    const form = document.getElementById("employeeForm");
    const btnAdd = document.getElementById("btnAdd");
    const btnCancel = document.querySelector("#employeeModal .btn-cancel");
    const sucursalSelect = document.getElementById("sucursal");
    const horarioSelect = document.getElementById("horario");
    const btnAgregar = document.getElementById("agregarHorario");
    const horariosAgregados = document.getElementById("horariosAgregados");
    
    // --- Elementos del DOM: Modal EDITAR (Principal) ---
    const editModal = document.getElementById("editEmployeeModal");
    
    // ** ELEMENTOS DEL FORMULARIO 1 (Datos Personales) **
    const employeeDataForm = document.getElementById("employeeDataForm");
    const employeeIdData = document.getElementById("employeeIdData");
    const horariosFlexiblesAdmin = document.getElementById("horariosFlexiblesAdmin");

    // ** ELEMENTOS DEL FORMULARIO 2 (Horarios Específicos) **
    // Estos eran los que faltaban y causaban el ReferenceError:
    const sucursalSelectEdit = document.getElementById("sucursalEdit");
    const horarioSelectEdit = document.getElementById("horarioEdit");
    const btnAgregarEdit = document.getElementById("agregarHorarioEdit"); // <-- Faltaba
    const horariosAgregadosEdit = document.getElementById("horariosAgregadosEdit");
    // ⬇️ NUEVA DECLARACIÓN ⬇️
    const btnAddScheduleFromEdit = document.getElementById("btnAddScheduleFromEdit");

    // ** ELEMENTOS DE ENVÍO DE HORARIOS (Botones y Form) **
    const scheduleDataForm = document.getElementById("scheduleDataForm");
    const employeeIdSchedule = document.getElementById("employeeIdSchedule");
    const btnGuardarHorarios = document.getElementById("btnGuardarHorarios");
    const btnCancelarHorarios = document.getElementById("btnCancelarHorarios");

    // --- Elementos del DOM: Comunes ---
    const closeButtons = document.querySelectorAll(".close");
    const searchInput = document.getElementById("searchInput");
    const tableBody = document.getElementById("employeeTableBody");

    // --- Elementos del DOM: Modal de Horarios (el pequeño para crear horarios nuevos) ---
    const scheduleModal = document.getElementById("scheduleModal");
    const btnAddSchedule = document.getElementById("btnAddSchedule");
    const scheduleForm = document.getElementById("scheduleForm");
    const cancelAddSchedule = document.getElementById("cancelAddSchedule");

    // --- Elementos del DOM: Botones de Exportación ---
    const btnExportExcel = document.getElementById("btnExportExcel");
    const btnExportPDF = document.getElementById("btnExportPDF");
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

    cargarSucursales(sucursalSelect);
    cargarHorarios(horarioSelect);
  });

  // =================================================================
  // ABRIR MODAL DE EDICIÓN (Botones verdes en la tabla)
  // =================================================================
  tableBody.addEventListener("click", (e) => {
    // Busca el botón de editar más cercano al que se hizo clic
    const editButton = e.target.closest(".btn-editar");

    // Si se hizo clic en un botón de editar
if (editButton) {
    e.preventDefault(); 
    
    const data = editButton.dataset; 
    const empId = data.id; 
    
    // ----------------------------------------------------------
    // 1. RELLENAR CAMPOS DE DATOS PERSONALES (Formulario 1)
    // ----------------------------------------------------------
    
    // ⚠️ ID para Visualización (Asumo que es para el campo 'ID de Empleado' de solo lectura)
    // Si esta es la línea que falla, significa que el ID es incorrecto en tu HTML.
    document.getElementById('employeeIndexDisplay').value = empId; 
    
    // Rellenar Códigos y Nombres
    document.getElementById('codigoFrappeEdit').value = data.frappe;
    document.getElementById('codigoChecadorEdit').value = data.checador;
    document.getElementById('nombreEdit').value = data.nombre;
    document.getElementById('primerApellidoEdit').value = data.paterno;
    document.getElementById('segundoApellidoEdit').value = data.materno;
    document.getElementById('emailEdit').value = data.email;
    
    // ----------------------------------------------------------------
    // 2. CONEXIÓN DE LOS DOS FORMULARIOS SEPARADOS
    // ----------------------------------------------------------------
    
    // A. Formulario 1 (Datos Personales)
    document.getElementById('employeeIdData').value = empId; // Input oculto para envío
    employeeDataForm.action = `/empleados/editar-datos-basicos/${empId}/`;
    
    // B. Formulario 2 (Horarios)
    employeeIdSchedule.value = empId; // Input oculto para envío
    scheduleDataForm.action = `/empleados/editar/${empId}/`;
    
    // ----------------------------------------------------------------
    
    // Limpia horarios previos 
    horariosAgregadosEdit.innerHTML = `<div class="empty-schedule">Cargando horarios...</div>`;

    // 3. Llama a las APIs para rellenar los <select>
    cargarSucursales(sucursalSelectEdit); 
    cargarHorarios(horarioSelectEdit);  
    cargarHorariosAsignados(empId); 

    // 4. Muestra el modal de EDICIÓN
    const editModal = document.getElementById("editEmployeeModal");
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
// =================================================================
// LÓGICA DE ENVÍO Y SERIALIZACIÓN PARA GUARDAR ASIGNACIONES (Formulario 2)
// ESTA FUNCIÓN RESUELVE TU PROBLEMA
// =================================================================

// Las variables scheduleDataForm, horariosAgregadosEdit, sucursalSelectEdit y horarioSelectEdit ya están definidas al inicio del script.
if (scheduleDataForm) {
    scheduleDataForm.addEventListener("submit", async function (e) {
        e.preventDefault(); 
        
        const form = this; 
        const horariosRestantes = horariosAgregadosEdit.querySelectorAll('.schedule-label');
        
        // --- 1. VALIDACIÓN (Lógica Correcta) ---
        if (horariosRestantes.length === 0) {
            if (sucursalSelectEdit.value || horarioSelectEdit.value) {
                alert("⚠️ Por favor, agregue el horario a la lista con el botón '+' o asegúrese de que los selectores estén vacíos antes de guardar.");
                return; 
            }
        }
        
        // --- 2. SERIALIZACIÓN: RECOLECCIÓN DE TAGS Y DATOS OCULTOS ---
        
        // Creamos un nuevo FormData para evitar conflictos con el formulario original
        const finalFormData = new FormData();
        
        // 1. Añadir el token CSRF (desde csrf.js: cookie o <meta name="csrf-token">)
        const csrfToken = getCSRFToken();
        finalFormData.append('csrfmiddlewaretoken', csrfToken);
        
        // 2. Añadir el ID del empleado
        finalFormData.append('empleado_id', employeeIdSchedule.value); 
        
        // 🟢 CÓDIGO A INSERTAR: SERIALIZACIÓN DE CAMPOS SUPERIORES (SELECTS Y CHECKBOXES)

        // Serializar Sucursal y Horario (se envían aunque estén vacíos)
        finalFormData.append('sucursalEdit', document.getElementById('sucursalEdit').value);
        finalFormData.append('horarioEdit', document.getElementById('horarioEdit').value);

        // Serializar los checkboxes de días seleccionados (si hay alguno para agregar)
        document.querySelectorAll('#scheduleDataForm .day-selector .day-checkbox:checked').forEach(checkbox => {
            // Django espera arrays para los días, por eso usamos el mismo nombre que el tag.
            finalFormData.append('dias[]', checkbox.dataset.id); 
        });

        // 3. Recopilamos los datos de los inputs ocultos dentro de los tags negros restantes
        horariosRestantes.forEach(etiqueta => {
            etiqueta.querySelectorAll('input[type="hidden"]').forEach(input => {
                // Esto añade sucursales[], horarios[], y dias[] al FormData
                finalFormData.append(input.name, input.value);
            });
        });
        
        // --- 3. ENVÍO ASÍNCRONO FINAL ---
        try {
            const response = await fetch(form.action, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCSRFToken() },
                body: finalFormData,
            });

            if (response.ok) {
                // Éxito al guardar: Cerramos modal y recargamos la página.
                const editModal = document.getElementById("editEmployeeModal");
                editModal.style.display = 'none';
                
                alert('✅ Asignaciones de horario guardadas y actualizadas.');
                window.location.reload(); 
                
            } else {
                // Si la respuesta no es OK (ej. error 400), alertamos al usuario.
                const errorText = await response.text();
                alert('❌ Error al guardar asignaciones. El servidor rechazó los datos.');
                console.error("Error del servidor:", errorText);
            }
        } catch (error) {
            console.error('Error de red al guardar asignaciones:', error);
            alert('❌ Error de conexión al servidor.');
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

// ⬇️ AÑADE TU NUEVO CÓDIGO AQUÍ ⬇️
// Nuevo manejador para el botón Cancelar del Formulario 1 (Datos Personales)
const btnCancelData = document.querySelector("#editEmployeeModal .btn-cancel-data");
if (btnCancelData) {
    btnCancelData.addEventListener("click", () => {
        const editModal = document.getElementById("editEmployeeModal");
        editModal.style.display = "none";
    });
}
// ⬆️ FIN DEL CÓDIGO AÑADIDO ⬆️

// ⬇️ MANEJADOR PARA EL BOTÓN CANCELAR DEL FORMULARIO 2 (Horarios) ⬇️
if (btnCancelarHorarios) {
    btnCancelarHorarios.addEventListener("click", () => {
        const editModal = document.getElementById("editEmployeeModal");
        editModal.style.display = "none";
    });
}
// ⬆️ FIN DEL CÓDIGO AÑADIDO ⬆️

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
// Añadir esta función en gestion_empleados.js, cerca de las funciones cargar...
function actualizarListaHorariosFlexibles(horarios) {
    const listContainer = document.getElementById('horariosFlexiblesAdmin');
    if (!listContainer) return;

    listContainer.innerHTML = ''; 
    let flexibleCount = 0;

    horarios.forEach(horario => {
        // Solo mostramos el botón de eliminación para horarios flexibles
        if (horario.es_flexible) {
            flexibleCount++;
            const itemDiv = document.createElement('div');
            itemDiv.classList.add('horario-flexible-item'); 
            itemDiv.innerHTML = `
                <span>${horario.texto}</span>
                <button type="button" class="btn-eliminar-horario" data-id="${horario.id}">
                    <i class="fas fa-times"></i>
                </button>
            `;
            
            // 🟢 MANEJADOR DE CLIC:
            itemDiv.querySelector('.btn-eliminar-horario').addEventListener('click', async function(e) {
                e.preventDefault();
                // ⚠️ Se agregó esta línea para evitar la propagación si hay selects cerca
                e.stopPropagation(); 
                
                if (confirm(`¿Estás seguro de eliminar el horario: ${horario.texto}?`)) {
                    const selectElement = document.getElementById('horarioEdit');

                    const success = await eliminarHorario(this.dataset.id);
                    if (success) {
                        // Recargar la lista DESPUÉS de eliminar
                        await cargarHorarios(selectElement); 
                    }
                }
            });
            
            listContainer.appendChild(itemDiv);
        }
    });

    if (flexibleCount === 0) {
        listContainer.innerHTML = '<p class="text-muted" style="text-align: center;">No hay horarios flexibles para administrar.</p>';
    }
}
// REEMPLAZAR la función cargarHorarios existente con esta versión
async function cargarHorarios(selectElement) {
    if (!selectElement) return null;

    try {
        const response = await fetch('/api/lista_horarios/');
        if (!response.ok) throw new Error('Error al cargar horarios');
        
        const horarios = await response.json();

        // 1. Limpiar y rellenar el SELECT
        selectElement.innerHTML = '<option value="" disabled selected>Seleccione...</option>';
        let lastHorarioId = null;

        horarios.forEach(horario => {
            // Llenar el SELECT principal
            const option = document.createElement('option');
            option.value = horario.id;
            option.textContent = horario.texto; 
            
            // ⚠️ Importante: Mantenemos el flag de flexibilidad para la futura lista de borrado
            option.dataset.flexible = horario.es_flexible; 

            selectElement.appendChild(option);
            lastHorarioId = horario.id; 
        });

        // 2. Llenar la lista de administración de horarios flexibles
        // 🟢 NUEVA LLAMADA: Llamamos a una nueva función que se encargará de crear la lista de botones "X".
        actualizarListaHorariosFlexibles(horarios); 

        return lastHorarioId;

    } catch (error) {
        console.error('Error en cargarHorarios:', error);
        return null;
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

// =================================================================
// 3. ABRIR MODAL PEQUEÑO DESDE EL MODAL GRANDE DE EDICIÓN
// =================================================================
if (btnAddScheduleFromEdit) {
    btnAddScheduleFromEdit.addEventListener("click", function (e) {
        e.preventDefault();
        
        // 1. Mostrar el modal pequeño (Agregar Horario)
        scheduleModal.style.display = "flex";
        
        // 2. Limpiar y establecer valores por defecto
        scheduleForm.reset();
        document.querySelector('input[name="cruzaNoche"][value="no"]').checked = true; // Por defecto a "No"
        document.getElementById("horaEntrada").focus();
    });
}
// ⬇️ LÓGICA DE ENVÍO ASÍNCRONO DEL MODAL PEQUEÑO (FINAL) ⬇️
if (scheduleForm) {
    scheduleForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        
        const formData = new FormData(scheduleForm);
        
        try {
            const response = await fetch(scheduleForm.action, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const scheduleModal = document.getElementById('scheduleModal');
                const horarioSelectEdit = document.getElementById('horarioEdit');

                // 1. CERRAR EL MODAL PEQUEÑO
                scheduleModal.style.display = 'none';
                
                // 2. RECARGAR EL SELECT Y OBTENER EL ID DEL ÚLTIMO ELEMENTO
                // ⚠️ CAMBIO CRÍTICO: Aquí almacenamos el ID devuelto por la función
                const newHorarioId = await cargarHorarios(horarioSelectEdit); 
                
                // 3. SELECCIONAR EL HORARIO RECIÉN CREADO EN EL DROPDOWN
                if (newHorarioId) {
                    horarioSelectEdit.value = newHorarioId; // ⬅️ SELECCIONA el nuevo valor.
                }
                
                alert('✅ Horario creado y lista actualizada.');
                
            } else {
                // Manejar errores
                const errorData = await response.json();
                alert(`⚠️ Error al crear horario: ${errorData.error || 'Verifique los datos.'}`);
            }
        } catch (error) {
            console.error('Error al enviar horario:', error);
            alert('❌ Error de conexión o servidor.');
        }
    });
}
});

// 🟢 FUNCIÓN DE ELIMINACIÓN DE API (Añadir al final de gestion_empleados.js)
async function eliminarHorario(horarioId) {
    const csrfToken = getCSRFToken();
    
    try {
        const response = await fetch(`/api/horarios/eliminar/${horarioId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrfToken 
            }
        });

        if (response.ok) {
            alert('Horario eliminado exitosamente.');
            return true;
        } else {
            const error = await response.json();
            alert(`Fallo la eliminación: ${error.error}`);
            return false;
        }
    } catch (error) {
        console.error('Error de red al eliminar:', error);
        alert('Error de conexión al servidor.');
        return false;
    }
}
// =================================================================
// LÓGICA DE EXPORTACIÓN A EXCEL (DESCARGA DE LISTA DE EMPLEADOS)
// =================================================================

if (btnExportExcel) {
    btnExportExcel.addEventListener("click", function (e) {
        e.preventDefault(); 
        
        // 🟢 1. OBTENER EL VALOR DE BÚSQUEDA
        // Asumiendo que 'searchInput' es el elemento <input> del buscador.
        const searchInput = document.getElementById("searchInput"); 
        const searchValue = searchInput ? searchInput.value.trim() : '';

        // 2. Definir la URL base
        let urlDeDescarga = "/admin-gestion-empleados/exportar/excel/"; 
        
        // 🟢 3. AÑADIR EL PARÁMETRO DE BÚSQUEDA a la URL si existe un valor
        if (searchValue) {
            // Usamos encodeURIComponent para manejar espacios y caracteres especiales
            urlDeDescarga += `?q=${encodeURIComponent(searchValue)}`;
        }
        
        // --- MÉTODO INFALIBLE: FORZAR REDIRECCIÓN CON LA RUTA COMPLETA ---
        const baseUrl = window.location.origin;
        window.location.href = baseUrl + urlDeDescarga; // Envía la URL con o sin ?q=...
        
        // Opcional: Feedback visual durante la descarga
        this.disabled = true;
        this.textContent = "Descargando Excel...";
        
        setTimeout(() => {
            this.disabled = false;
            this.innerHTML = '<i class="fas fa-file-excel"></i> Exportar Excel';
        }, 5000); 
    });
}