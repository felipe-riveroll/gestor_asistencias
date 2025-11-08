// Variables globales
let charts = {};
let currentData = null; // Guardará toda la data: { branches: [], period_summary: {}, employee_summary_kpis: [], employee_performance_kpis: [] }
let activeTab = 'summary'; // Pestaña activa por defecto ('summary' o 'kpis')

// --- INICIALIZACIÓN ---
document.addEventListener('DOMContentLoaded', () => {
    initializeDashboard();
    loadInitialData(); // Carga los datos iniciales al abrir la página
});

function initializeDashboard() {
    // Configura fechas iniciales (Este Mes)
    const { startDate, endDate } = calculateDateRange('month'); // <-- Volvemos a 'month'
    document.getElementById('startDate').value = startDate;
    document.getElementById('endDate').value = endDate;
    document.getElementById('dateRange').value = 'month'; // <-- Volvemos a 'month'

    // Listeners Filtros Fecha
    document.getElementById('dateRange').addEventListener('change', handleDateRangeChange);
    document.getElementById('startDate').addEventListener('change', applyFiltersAutomatically);
    document.getElementById('endDate').addEventListener('change', applyFiltersAutomatically);

    // Listener Exportar Excel
    document.getElementById('exportExcelBtn').addEventListener('click', exportToExcelWithStyles);

    // Listener Buscador General
    document.getElementById('employeeSearchInput').addEventListener('input', handleSearch);

    // Listeners para Pestañas
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', function() {
            // Cambiar pestaña activa visualmente
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            this.classList.add('active');
            activeTab = this.getAttribute('data-tab'); // Actualiza variable global
            document.getElementById(activeTab).classList.add('active');

            // Refrescar la tabla AHORA visible con el filtro actual
            handleSearch();
        });
    });
    // Activa la primera pestaña por defecto
    document.querySelector('.tab-button[data-tab="summary"]').classList.add('active');
    document.getElementById('summary').classList.add('active');

    initializeCharts(); // Inicializa las gráficas
}

// Llama a loadInitialData con retraso
function applyFiltersAutomatically() {
    clearTimeout(window.filterTimeout);
    window.filterTimeout = setTimeout(loadInitialData, 300);
}

// Muestra/oculta inputs de fecha personalizada
function handleDateRangeChange() {
    const range = document.getElementById('dateRange').value;
    const customDatesWrapper = document.querySelector('.custom-dates-wrapper');
    if (range === 'custom') {
        customDatesWrapper.style.display = 'flex';
    } else {
        customDatesWrapper.style.display = 'none';
        applyFiltersAutomatically(); // Recarga si cambia a rango predefinido
    }
}

// --- CARGA DE DATOS ---
async function loadInitialData() {
    showLoadingState();
    try {
        const dateRange = document.getElementById('dateRange').value;
        let startDate = document.getElementById('startDate').value;
        let endDate = document.getElementById('endDate').value;

        if (dateRange !== 'custom') {
            const dates = calculateDateRange(dateRange);
            startDate = dates.startDate; endDate = dates.endDate;
            document.getElementById('startDate').value = startDate; document.getElementById('endDate').value = endDate;
        } else {
            if (!startDate || !endDate) { showErrorState('Fechas Incompletas', 'Selecciona fecha de inicio y fin.'); return; }
            if (new Date(startDate) > new Date(endDate)) { showErrorState('Fechas Inválidas', 'La fecha de inicio no puede ser posterior a la fecha de fin.'); return; }
        }

        const apiResponse = await fetchAllBranchesData(startDate, endDate); // Llama a la API

        // Verifica estructura completa de la respuesta
        if (apiResponse && typeof apiResponse === 'object' && apiResponse.branches !== undefined && apiResponse.employee_summary_kpis !== undefined && apiResponse.employee_performance_kpis !== undefined && apiResponse.period_summary !== undefined) {
             currentData = apiResponse; // Guarda datos globales
            if (apiResponse.branches.length > 0 || apiResponse.employee_summary_kpis.length > 0 || apiResponse.employee_performance_kpis.length > 0) {
                updateDashboard(currentData); // Actualiza UI
            } else {
                showNoData(); // Muestra "sin datos"
            }
        } else {
            console.error("Respuesta inesperada:", apiResponse);
            showErrorState('Error de Datos', 'Formato de respuesta inesperado.');
        }
    } catch (error) {
        console.error('Error en loadInitialData:', error);
        showErrorState('Error al Cargar', error.message || 'Intenta nuevamente.');
    }
}

function calculateDateRange(range) {
    const today = new Date(); let startDate = new Date(today); let endDate = new Date(today);
    switch(range) { 
        case 'today': 
            break; 
        case 'week': 
            const dayOfWeek = today.getDay();
            const diff = today.getDate() - dayOfWeek + (dayOfWeek === 0 ? -6 : 1);
            startDate = new Date(today.getFullYear(), today.getMonth(), diff);
            endDate = new Date();
            break; 
        
        // --- Lógica de "Mes" actualizada ---
        case 'month': 
            endDate = new Date(today); // Fecha de Hoy
            startDate = new Date(today);
            startDate.setMonth(startDate.getMonth() - 1); // Mismo día, un mes atrás
            break; 
        // --- FIN DEL CAMBIO ---

        case 'quarter': 
            const quarter = Math.floor(today.getMonth() / 3);
            startDate = new Date(today.getFullYear(), quarter * 3, 1);
            endDate = new Date(today.getFullYear(), quarter * 3 + 3, 0);
            break; 
        case 'year': 
            startDate = new Date(today.getFullYear(), 0, 1);
            endDate = new Date(today.getFullYear(), 11, 31);
            break; 
        default: 
            // Default ahora es tu nueva lógica de 'month'
            endDate = new Date(today);
            startDate = new Date(today);
            startDate.setMonth(startDate.getMonth() - 1);
    }
    const formatDate = (date) => { 
        const d = new Date(date); 
        if (isNaN(d.getTime())) return new Date().toISOString().split('T')[0]; 
        const month = '' + (d.getMonth() + 1);
        const day = '' + d.getDate();
        const year = d.getFullYear();
        return [year, month.padStart(2, '0'), day.padStart(2, '0')].join('-');
    }
    return { startDate: formatDate(startDate), endDate: formatDate(endDate) };
}

// --- LLAMADA REAL A LA API ---
async function fetchAllBranchesData(startDate, endDate) {
    
    // ===========================================
    // === ¡ESTE ES EL ÚNICO CAMBIO EN EL JS! ===
    // ===========================================
    console.log(`Cargando datos de NAVE de ${startDate} a ${endDate} desde la API...`);
    const apiUrl = `/api/dashboard/nave/?startDate=${startDate}&endDate=${endDate}`;
    
    try {
        const response = await fetch(apiUrl);
        if (!response.ok) { 
            let errorMessage = `Error ${response.status}: ${response.statusText}`; 
            try { 
                const errorData = await response.json(); 
                errorMessage = errorData?.error || errorMessage; 
            } catch (e) { /* Ignora */ } 
            console.error('Error en la respuesta de la API:', errorMessage); 
            throw new Error(errorMessage); 
        }
        const result = await response.json();
        if (!result.success) { 
            console.error('La API reportó un error:', result.error); 
            throw new Error(result.error || 'Error desconocido reportado por la API'); 
        }
        console.log("Datos recibidos de la API:", result.data);
        const defaultData = { 
            branches: [], 
            period_summary: { 
                total_attendances: 0, 
                total_permissions: 0, 
                total_absences: 0, 
                total_justified_absences: 0 
            }, 
            employee_summary_kpis: [], 
            employee_performance_kpis: [] 
        };
        // Asegura que todas las propiedades esperadas existan, incluso si la API devuelve {}
        const receivedData = result.data || {};

        return {
             branches: receivedData.branches || [],
             period_summary: receivedData.period_summary || defaultData.period_summary,
             employee_summary_kpis: receivedData.employee_summary_kpis || [],
             employee_performance_kpis: receivedData.employee_performance_kpis || []
        };
    } catch (error) { 
        console.error('Falló la llamada a fetchAllBranchesData:', error); 
        throw error; 
    }
}

// --- ACTUALIZACIÓN DE UI ---
function updateDashboard(data) {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('noDataMessage').style.display = 'none';
    document.getElementById('dashboardContent').style.display = 'block';
    document.getElementById('exportExcelBtn').disabled = false;
    
    updateMainKPIs(data);
    updateAllCharts(data);
    handleSearch(); // Llama al buscador para que actualice la tabla ACTIVA
}

function updateMainKPIs(data) {
    const branches = data?.branches || [];
    const totalEmployees = branches.reduce((sum, b) => sum + (b?.employees || 0), 0);
    const avgEfficiency = branches.length > 0 ? branches.reduce((sum, b) => sum + (b?.efficiency || 0), 0) / branches.length : 0;
    const avgPunctuality = branches.length > 0 ? branches.reduce((sum, b) => sum + (b?.punctuality || 0), 0) / branches.length : 0;
    const totalAbsences = data?.period_summary?.total_absences || 0; // Faltas Injustificadas
    document.getElementById('totalEmployees').textContent = totalEmployees.toLocaleString();
    document.getElementById('avgEfficiency').textContent = `${avgEfficiency.toFixed(1)}%`;
    document.getElementById('avgPunctuality').textContent = `${avgPunctuality.toFixed(1)}%`;
    document.getElementById('totalAbsences').textContent = totalAbsences.toLocaleString();
}

// --- Actualizar Tabla Resumen Horas Empleado ---
function updateEmployeeSummaryTable() {
    const tbody = document.getElementById('employeeSummaryTableBody');
    const searchInput = document.getElementById('employeeSearchInput');
    const searchTerm = searchInput.value.toLowerCase().trim();
    tbody.innerHTML = '';
    const colspanValue = 7; // ID, Empleado, Hrs Trab, Hrs Plan, Var, Ret, Aus

    let employeeData = currentData?.employee_summary_kpis || [];

    if (searchTerm) {
        employeeData = employeeData.filter(emp => {
            const idMatch = String(emp.ID || '').toLowerCase().includes(searchTerm);
            const nameMatch = String(emp.Empleado || '').toLowerCase().includes(searchTerm); // Usa 'Empleado'
            return idMatch || nameMatch;
        });
    }

    if (employeeData.length === 0) {
        const message = searchTerm ? 'No se encontraron empleados.' : 'No hay datos de resumen.';
        tbody.innerHTML = `<tr><td colspan="${colspanValue}" style="text-align:center;">${message}</td></tr>`;
        return;
    }

    employeeData.forEach(emp => {
        const hrsTrab = emp['Hrs. Trabajadas'] || '0:00:00';
        const hrsPlan = emp['Hrs. Planificadas'] || '0:00:00';
        const variacion = emp['Variación'] || '0:00:00';
        const retardos = emp.Retardos !== undefined ? emp.Retardos : 0;
        const ausencias = emp.Ausencias !== undefined ? emp.Ausencias : 0; // Faltas injustificadas

        tbody.innerHTML += `
            <tr>
                <td>${emp.ID || 'N/A'}</td>
                <td>${emp.Empleado || 'Sin Nombre'}</td>
                <td>${hrsTrab}</td>
                <td>${hrsPlan}</td>
                <td>${variacion}</td>
                <td>${retardos}</td>
                <td>${ausencias}</td>
            </tr>`;
    });
}

// --- Actualizar Tabla KPIs Rendimiento Empleado (CORREGIDA) ---
function updateEmployeeKPITable() {
    const tbody = document.getElementById('employeeKpiTableBody');
    const searchInput = document.getElementById('employeeSearchInput');
    const searchTerm = searchInput.value.toLowerCase().trim();
    tbody.innerHTML = '';
    
    // El colspan ahora es 7
    const colspanValue = 7; // ID, Nombre, Faltas Just, TasaAus, Punt, Efic, SIC

    let employeeData = currentData?.employee_performance_kpis || []; // <-- Lee de la lista correcta

    if (searchTerm) {
        employeeData = employeeData.filter(emp => {
            const idMatch = String(emp.ID || '').toLowerCase().includes(searchTerm);
            const nameMatch = String(emp.Nombre || '').toLowerCase().includes(searchTerm); // Usa 'Nombre'
            return idMatch || nameMatch;
        });
    }

    if (employeeData.length === 0) {
        const message = searchTerm ? 'No se encontraron empleados.' : 'No hay datos de KPIs.';
        tbody.innerHTML = `<tr><td colspan="${colspanValue}" style="text-align:center;">${message}</td></tr>`;
        return;
    }

    // --- LÓGICA DE COLOR CORREGIDA (BASADA EN TUS IMÁGENES) ---
    function getKpiClass(value, kpiType) { 
        if (value === null || value === undefined || isNaN(value)) return ''; 
        
        switch (kpiType) { 
            case 'faltas_just': // Lógica: 0-5=Verde, 6-10=Amarillo, >10=Rojo
                return value <= 5 ? 'kpi-cell-success' : value <= 10 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            
            case 'ausentismo': // Lógica: >=95=Verde, >=70=Amarillo, <70=Rojo
                return value >= 95 ? 'kpi-cell-success' : value >= 70 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            
            case 'puntualidad': // Lógica: >=95=Verde, >=70=Amarillo, <70=Rojo
                return value >= 95 ? 'kpi-cell-success' : value >= 70 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            
            case 'eficiencia': // Lógica: >=85=Verde, >=50=Amarillo, <50=Rojo
                return value >= 85 ? 'kpi-cell-success' : value >= 50 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            
            case 'sic': // Lógica: >=85=Verde, >=50=Amarillo, <50=Rojo
                return value >= 85 ? 'kpi-cell-success' : value >= 50 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            
            default: 
                return ''; 
        } 
    }

    employeeData.forEach(emp => {
        // --- Leer todos los datos ---
        const faltasJustVal = emp['Faltas Justificadas'];
        const ausentismoVal = emp['Tasa Ausentismo (%)'];
        const puntualidadVal = emp['Índice Puntualidad (%)'];
        const eficienciaVal = emp['Eficiencia Horas (%)'];
        const sicVal = emp['SIC'];

        // --- Obtener clases de color ---
        const faltasJustClass = getKpiClass(faltasJustVal, 'faltas_just');
        const ausentismoClass = getKpiClass(ausentismoVal, 'ausentismo');
        const puntualidadClass = getKpiClass(puntualidadVal, 'puntualidad');
        const eficienciaClass = getKpiClass(eficienciaVal, 'eficiencia');
        const sicClass = getKpiClass(sicVal, 'sic');

        // --- Formatear texto a mostrar ---
        const faltasJustStr = (faltasJustVal !== undefined && faltasJustVal !== null) ? faltasJustVal : '0';
        const ausentismoStr = ausentismoVal !== undefined ? ausentismoVal.toFixed(1) + '%' : 'N/A';
        const eficienciaStr = eficienciaVal !== undefined ? eficienciaVal.toFixed(1) + '%' : 'N/A';
        const puntualidadStr = puntualidadVal !== undefined ? puntualidadVal.toFixed(1) + '%' : 'N/A';
        const sicStr = sicVal !== undefined ? sicVal.toFixed(1) : 'N/A';

        // --- Añadir la fila completa (7 celdas) ---
        tbody.innerHTML += `
            <tr>
                <td>${emp.ID || 'N/A'}</td>
                <td>${emp.Nombre || 'Sin Nombre'}</td>
                <td class="${faltasJustClass}">${faltasJustStr}</td> 
                <td class="${ausentismoClass}">${ausentismoStr}</td>
                <td class="${puntualidadClass}">${puntualidadStr}</td>
                <td class="${eficienciaClass}">${eficienciaStr}</td>
                <td class="${sicClass}">${sicStr}</td>
            </tr>`;
    });
}
// --- FIN DE LA FUNCIÓN ACTUALIZADA ---

// --- Manejador de Búsqueda ---
function handleSearch() {
    // Llama a la función de actualización de la tabla que esté ACTIVA
    if (activeTab === 'summary') {
        updateEmployeeSummaryTable();
    } else if (activeTab === 'kpis') {
        updateEmployeeKPITable();
    }
}

// --- MANEJO DE ESTADOS DE UI ---
function showLoadingState() { 
    document.getElementById('loadingState').style.display = 'block'; 
    document.getElementById('noDataMessage').style.display = 'none'; 
    document.getElementById('dashboardContent').style.display = 'none'; 
    document.getElementById('exportExcelBtn').disabled = true; 
}

function showNoData() { 
    const noDataMsgElement = document.getElementById('noDataMessage'); 
    noDataMsgElement.innerHTML = `<i class="fa-solid fa-info-circle" style="font-size: 50px; margin-bottom: 20px; color: var(--info-color);"></i><h2>No hay datos disponibles</h2><p>No se encontraron registros.</p>`; 
    noDataMsgElement.style.display = 'block'; 
    document.getElementById('loadingState').style.display = 'none'; 
    document.getElementById('dashboardContent').style.display = 'block'; 
    document.getElementById('exportExcelBtn').disabled = true; 
    
    // Limpia ambas tablas
    const summaryTbody = document.getElementById('employeeSummaryTableBody');
    if(summaryTbody) summaryTbody.innerHTML = `<tr><td colspan="7" style="text-align:center;">No hay datos.</td></tr>`; 
    
    const kpiTbody = document.getElementById('employeeKpiTableBody');
    if(kpiTbody) kpiTbody.innerHTML = `<tr><td colspan="7" style="text-align:center;">No hay datos.</td></tr>`; 

    Object.values(charts).forEach(chart => { 
        chart.data.labels = []; 
        chart.data.datasets = []; 
        chart.update(); 
    }); 
}

function showErrorState(title, message) { 
    const noData = document.getElementById('noDataMessage'); 
    noData.innerHTML = `<i class="fa-solid fa-exclamation-triangle" style="font-size: 50px; margin-bottom: 20px; color: var(--danger-color);"></i><h2>${title}</h2><p>${message}</p>`; 
    document.getElementById('loadingState').style.display = 'none'; 
    noData.style.display = 'block'; 
    document.getElementById('dashboardContent').style.display = 'none'; 
    document.getElementById('exportExcelBtn').disabled = true; 
}

// --- GRÁFICAS (Chart.js) ---
function initializeCharts() { 
    const commonOptions = { responsive: true, maintainAspectRatio: false }; 
    charts.branchEfficiencyChart = new Chart('branchEfficiencyChart', { 
        type: 'bar', 
        options: { 
            ...commonOptions, 
            plugins: { legend: { display: false } }, 
            scales: { y: { beginAtZero: true, max: 100 } } 
        } 
    }); 
    charts.sicDistributionChart = new Chart('sicDistributionChart', { 
        type: 'doughnut', 
        options: { 
            ...commonOptions, 
            plugins: { legend: { position: 'bottom' } } 
        } 
    }); 
    charts.periodEventsChart = new Chart('periodEventsChart', { 
        type: 'bar', 
        options: { 
            ...commonOptions, 
            plugins: { legend: { display: false } }, 
            scales: { y: { beginAtZero: true, title: { display: true, text: 'Total Ocurrencias' } } } 
        } 
    }); 
    charts.topEfficiencyChart = new Chart('topEfficiencyChart', { 
        type: 'bar', 
        options: { 
            ...commonOptions, 
            indexAxis: 'y', 
            plugins: { legend: { display: false } }, 
            scales: { x: { beginAtZero: true } } 
        } 
    }); 
    charts.branchComparisonChart = new Chart('branchComparisonChart', { 
        type: 'radar', 
        options: { 
            ...commonOptions, 
            scales: { r: { beginAtZero: true, max: 100 } } 
        } 
    }); 
}

// --- FUNCIÓN DE GRÁFICAS (ACTUALIZADA) ---
function updateAllCharts(data) { 
    const branches = data?.branches || []; 
    const summary = data?.period_summary || { 
        total_attendances: 0, 
        total_permissions: 0, 
        total_absences: 0, 
        total_justified_absences: 0 
    }; 
    const color = (variable) => getComputedStyle(document.documentElement).getPropertyValue(variable).trim(); 
    
    // --- Gráfica 1: Eficiencia por Sucursal (Ahora solo mostrará 1 barra de Nave) ---
    charts.branchEfficiencyChart.data = { 
        labels: branches.map(b => b.name || 'N/A'), 
        datasets: [{ 
            data: branches.map(b => b.efficiency || 0), 
            backgroundColor: color('--primary-color') 
        }] 
    }; 
    
    // --- Gráfica 2: Distribución de SIC (Basada en empleados) ---
    const sicRanges = { 
        'Excelente (>=85)': 0, 
        'Bueno (70-84)': 0,
        'Regular (50-69)': 0,
        'Crítico (<50)': 0 
    }; 
    
    const kpiData = currentData?.employee_performance_kpis || [];
    kpiData.forEach(emp => { 
        const sic = emp.SIC || 0; 
        if (sic >= 85) sicRanges['Excelente (>=85)']++; 
        else if (sic >= 70) sicRanges['Bueno (70-84)']++;
        else if (sic >= 50) sicRanges['Regular (50-69)']++;
        else sicRanges['Crítico (<50)']++; 
    }); 
    
    charts.sicDistributionChart.data = { 
        labels: Object.keys(sicRanges), 
        datasets: [{ 
            data: Object.values(sicRanges), 
            backgroundColor: [
                color('--success-color'), // Excelente
                color('--info-color'),    // Bueno
                color('--warning-color'), // Regular
                color('--danger-color')   // Crítico
            ] 
        }] 
    }; 
    
    // --- Gráfica 3: Eventos del Periodo ---
    charts.periodEventsChart.data = { 
        labels: ['Asistencias', 'Permisos', 'Faltas', 'F. Justificadas'], 
        datasets: [{ 
            data: [
                summary.total_attendances || 0, 
                summary.total_permissions || 0, 
                summary.total_absences || 0, 
                summary.total_justified_absences || 0
            ], 
            backgroundColor: [
                color('--success-color'), 
                color('--info-color'), 
                color('--danger-color'), 
                color('--warning-color')
            ] 
        }] 
    }; 
    charts.periodEventsChart.options.scales.y.title.text = 'Total Ocurrencias'; 
    
    // --- Gráfica 4: Top Empleados por Eficiencia (¡LA QUE QUERÍAS!) ---
    const topEmployees = [...kpiData].sort((a, b) => (b['Eficiencia Horas (%)'] || 0) - (a['Eficiencia Horas (%)'] || 0)).slice(0, 10); 

    const efficiencyColors = topEmployees.map(emp => {
        const eficiencia = emp['Eficiencia Horas (%)'] || 0;
        if (eficiencia >= 85) return color('--success-color');
        if (eficiencia >= 50) return color('--warning-color');
        return color('--danger-color');
    });

    charts.topEfficiencyChart.data = { 
        labels: topEmployees.map(b => b.Nombre || 'N/A'), // Usa 'Nombre' de empleado
        datasets: [{ 
            data: topEmployees.map(b => b['Eficiencia Horas (%)'] || 0), // Usa 'Eficiencia Horas (%)'
            backgroundColor: efficiencyColors // <-- Usa los colores dinámicos
        }] 
    }; 
    
    // --- Gráfica 5: Comparativa (No se usa) ---
    const radarLabels = ['Eficiencia', 'Puntualidad', 'SIC', 'Productividad']; 
    charts.branchComparisonChart.data = { 
        labels: radarLabels, 
        datasets: branches.slice(0, 4).map((b, i) => { 
            return { 
                label: b.name || `Sucursal ${i+1}`, 
                data: [b.efficiency || 0, b.punctuality || 0, b.avgSIC || 0, b.productivity || 0], 
                backgroundColor: 'rgba(133, 30, 35, 0.5)', 
                borderColor: 'rgba(133, 30, 35, 1)', 
                borderWidth: 2 
            }; 
        }) 
    }; 
    
    // Actualiza todas las gráficas
    Object.values(charts).forEach(chart => chart.update()); 
}

// --- EXPORTACIÓN A EXCEL (LLAMA AL BACKEND CON POST) ---
async function exportToExcelWithStyles() {
    if (!currentData || (!currentData.branches?.length && !currentData.employee_summary_kpis?.length && !currentData.employee_performance_kpis?.length)) {
        alert('No hay datos cargados para exportar.');
        return;
    }

    const btn = document.getElementById('exportExcelBtn');
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Preparando...';
    btn.disabled = true;

    // Fechas solo para el nombre del archivo
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const filename = `Dashboard_Analisis_Nave_${startDate}_a_${endDate}.xlsx`; // Nombre de archivo actualizado

    try {
        // Usamos fetch con POST para ENVIAR los datos que ya tenemos
        const response = await fetch('/api/export_dashboard_excel/', { // Apuntamos a la misma URL de exportación
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // Asegúrate de incluir el token CSRF
                'X-CSRFToken': getCookie('csrftoken') 
            },
            body: JSON.stringify(currentData) // ¡Aquí enviamos los datos!
        });

        if (!response.ok) {
            // Si el servidor falla, muestra el error
            let errorMsg = `Error ${response.status}`;
            try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorMsg;
            } catch(e) {
                // El error no fue JSON
                errorMsg = await response.text();
            }
            throw new Error(errorMsg);
        }

        // El backend nos devuelve el archivo, no un JSON
        const blob = await response.blob();
        
        // Creamos un link en memoria para descargar el archivo
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename; // Usamos el nombre de archivo con las fechas
        document.body.appendChild(a);
        a.click(); // Inicia la descarga
        
        // Corrección para Opera: Da un pequeño margen antes de limpiar el enlace
        setTimeout(() => {
            window.URL.revokeObjectURL(url);
            if (document.body.contains(a)) {
                document.body.removeChild(a);
            }
        }, 100); // 100 milisegundos

    } catch (error) {
        console.error('Error al exportar Excel:', error);
        alert('Error al generar el archivo: ' + error.message);
    } finally {
        // Reactiva el botón
        btn.innerHTML = '<i class="fa-solid fa-file-excel"></i> Exportar a Excel';
        btn.disabled = false;
    }
}

// --- FUNCIÓN AUXILIAR PARA CSRF TOKEN ---
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}