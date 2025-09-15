document.addEventListener('DOMContentLoaded', () => {

    // Simulación de datos (reemplazar con tu llamada a la API si es necesario)
    const datosCompletos = {
        "31pte": [
            { noEmp: "1001", nombre: "Ana Gómez", unidad: "Contabilidad", fechaGen: "2025-08-01", motivo: "Horas Extra", responsable: "J. Martínez", horasGen: "8", fechasTomadas: "2025-08-05, 2025-08-06", horasTomadas: "4", restante: "4", actualizacion: "2025-08-07", observaciones: "Ninguna" },
            { noEmp: "1002", nombre: "Luis Pérez", unidad: "Ventas", fechaGen: "2025-08-02", motivo: "Compensación", responsable: "M. López", horasGen: "6", fechasTomadas: "2025-08-04", horasTomadas: "6", restante: "0", actualizacion: "2025-08-06", observaciones: "" }
        ],
        "villas": [
            { noEmp: "2001", nombre: "María Rodríguez", unidad: "Logística", fechaGen: "2025-08-03", motivo: "Horas Extra", responsable: "R. Sánchez", horasGen: "5", fechasTomadas: "2025-08-07", horasTomadas: "2", restante: "3", actualizacion: "2025-08-08", observaciones: "Revisión pendiente" }
        ],
        "nave": [],
        "rioblanco": []
    };

    // Referencias a los elementos del DOM
    const sucursalSelect = document.getElementById('sucursal');
    const searchInput = document.getElementById('searchInput'); // <-- NUEVO: Selector para la búsqueda
    const tbody = document.getElementById('reporteBody');
    const downloadBtn = document.getElementById('downloadBtn');

    function cargarDatos() {
        // Obtenemos los valores actuales de los filtros
        const sucursal = sucursalSelect.value;
        const terminoBusqueda = searchInput.value.toLowerCase().trim(); // <-- NUEVO: Obtenemos el texto a buscar

        tbody.innerHTML = ''; // Limpiamos la tabla

        let datos = [];
        // Seleccionamos los datos base según la sucursal
        if (sucursal === 'all' || sucursal === "") { // Asumimos que "" es igual a "todas"
            datos = Object.values(datosCompletos).flat();
        } else if (datosCompletos[sucursal]) {
            datos = datosCompletos[sucursal];
        }

        // <-- INICIO DE LA LÓGICA DE FILTRADO -->
        let datosFiltrados = datos;
        if (terminoBusqueda) {
            datosFiltrados = datos.filter(registro => {
                const nombre = registro.nombre.toLowerCase();
                const noEmp = registro.noEmp.toString();
                return nombre.includes(terminoBusqueda) || noEmp.includes(terminoBusqueda);
            });
        }
        // <-- FIN DE LA LÓGICA DE FILTRADO -->

        // Mostramos los datos filtrados o un mensaje si no hay resultados
        if (datosFiltrados.length === 0) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 12; // Ajusta al número de columnas de tu tabla
            td.className = "no-data";
            td.textContent = 'No se encontraron registros que coincidan con los filtros.';
            tr.appendChild(td);
            tbody.appendChild(tr);
            return;
        }

        datosFiltrados.forEach(registro => {
            const tr = document.createElement('tr');
            // Asegúrate que los campos coincidan con tu tabla HTML
            const campos = ['noEmp', 'nombre', 'unidad', 'fechaGen', 'motivo', 'responsable', 'horasGen', 'fechasTomadas', 'horasTomadas', 'restante', 'actualizacion', 'observaciones'];
            campos.forEach(campo => {
                const td = document.createElement('td');
                td.textContent = registro[campo] || '';
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    }
    
    // Función de descarga (no necesita cambios)
    function descargarExcel() {
        // ... (Tu función de descarga actual puede permanecer aquí)
    }

    // --- EVENT LISTENERS ---
    
    // Se ejecuta cuando cambia la sucursal
    sucursalSelect.addEventListener('change', cargarDatos);

    // <-- NUEVO: Se ejecuta cada vez que el usuario escribe en la barra de búsqueda -->
    searchInput.addEventListener('input', cargarDatos);
    
    downloadBtn.addEventListener('click', descargarExcel);

    // Carga inicial (tabla vacía)
    cargarDatos();
});