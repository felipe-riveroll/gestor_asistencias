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
    const { startDate, endDate } = calculateDateRange('month');
    document.getElementById('startDate').value = startDate;
    document.getElementById('endDate').value = endDate;
    document.getElementById('dateRange').value = 'month';

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
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            this.classList.add('active');
            activeTab = this.getAttribute('data-tab');
            document.getElementById(activeTab).classList.add('active');
            handleSearch();
        });
    });
    // Activa la primera pestaña por defecto
    document.querySelector('.tab-button[data-tab="summary"]').classList.add('active');
    document.getElementById('summary').classList.add('active');

    initializeCharts();
}

function applyFiltersAutomatically() {
    clearTimeout(window.filterTimeout);
    window.filterTimeout = setTimeout(loadInitialData, 300);
}

function handleDateRangeChange() {
    const range = document.getElementById('dateRange').value;
    const customDatesWrapper = document.querySelector('.custom-dates-wrapper');
    if (range === 'custom') {
        customDatesWrapper.style.display = 'flex';
    } else {
        customDatesWrapper.style.display = 'none';
        applyFiltersAutomatically();
    }
}

// --- CARGA DE DATOS (Corregida) ---
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

        const apiResponse = await fetchDashboardData(startDate, endDate);

        if (apiResponse && typeof apiResponse === 'object' && apiResponse.branches !== undefined && apiResponse.employee_summary_kpis !== undefined && apiResponse.employee_performance_kpis !== undefined && apiResponse.period_summary !== undefined) {
            currentData = apiResponse;
            if (apiResponse.branches.length > 0 || apiResponse.employee_summary_kpis.length > 0 || apiResponse.employee_performance_kpis.length > 0) {
                updateDashboard(currentData);
            } else {
                showNoData();
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
        case 'month':
            // --- CORRECCIÓN LÓGICA ---
            // "Este Mes" (del 1ro a hoy), basado en el comentario de initializeDashboard
            startDate = new Date(today.getFullYear(), today.getMonth(), 1);
            endDate = new Date(today);
            break;
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
            // Default (igual a 'month' corregido)
            startDate = new Date(today.getFullYear(), today.getMonth(), 1);
            endDate = new Date(today);
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

// --- LLAMADA A LA API (Corregida) ---
async function fetchDashboardData(startDate, endDate) {
    // --- CORRECCIÓN (Sintaxis) ---
    console.log(`Cargando datos del Dashboard General de ${startDate} a ${endDate} desde la API...`);
    
    // --- CORRECCIÓN (Sintaxis) ---
    const apiUrl = `/api/dashboard/general/?startDate=${startDate}&endDate=${endDate}`;

    try {
        const response = await fetch(apiUrl);
        if (!response.ok) {
            // --- CORRECCIÓN (Sintaxis) ---
            let errorMessage = `Error ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
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
        const receivedData = result.data || {};

        return {
             branches: receivedData.branches || [],
             period_summary: receivedData.period_summary || defaultData.period_summary,
             employee_summary_kpis: receivedData.employee_summary_kpis || [],
             employee_performance_kpis: receivedData.employee_performance_kpis || []
        };
    } catch (error) {
        console.error('Falló la llamada a fetchDashboardData:', error);
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
    updateBranchesTable(data); // Llama a la función que dibuja la tabla de sucursales
    handleSearch();
}

function updateMainKPIs(data) {
    // --- FILTRO: Excluir "Rio Blanco" del KPI de "Total Empleados" ---
    const branches = (data?.branches || []).filter(b => b.name && b.name.toLowerCase() !== 'rio blanco');
    
    const totalEmployees = branches.reduce((sum, b) => sum + (b?.employees || 0), 0);
    const avgEfficiency = branches.length > 0 ? branches.reduce((sum, b) => sum + (b?.efficiency || 0), 0) / branches.length : 0;
    const avgPunctuality = branches.length > 0 ? branches.reduce((sum, b) => sum + (b?.punctuality || 0), 0) / branches.length : 0;
    const totalAbsences = data?.period_summary?.total_absences || 0;
    
    document.getElementById('totalEmployees').textContent = totalEmployees.toLocaleString();
    // --- CORRECCIÓN (Sintaxis) ---
    document.getElementById('avgEfficiency').textContent = `${avgEfficiency.toFixed(1)}%`;
    // --- CORRECCIÓN (Sintaxis) ---
    document.getElementById('avgPunctuality').textContent = `${avgPunctuality.toFixed(1)}%`;
    document.getElementById('totalAbsences').textContent = totalAbsences.toLocaleString();
}

// --- FUNCIÓN DE TABLA DE SUCURSALES (ACTUALIZADA) ---
function updateBranchesTable(data) {
    const tbody = document.getElementById('summaryTableBody'); // Usa el ID de tu HTML 'grafica_general.html'
    if (!tbody) {
        console.warn("No se encontró el elemento 'summaryTableBody'.");
        return; 
    }
    
    tbody.innerHTML = '';
    // --- FILTRO: Excluir "Rio Blanco" de la tabla ---
    const branches = (data?.branches || []).filter(b => b.name && b.name.toLowerCase() !== 'rio blanco');

    if (branches.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No hay datos de sucursales.</td></tr>';
        return;
    }

    let totalEmployees = 0;
    let sumEfficiency = 0;
    let sumPunctuality = 0;
    let sumAvgSic = 0;
    let totalAbsences = 0;
    
    branches.forEach(branch => {
        totalEmployees += branch.employees || 0;
        sumEfficiency += branch.efficiency || 0;
        sumPunctuality += branch.punctuality || 0;
        sumAvgSic += branch.avgSIC || 0;
        totalAbsences += branch.absences || 0;

        // Lógica de color de JS (Corregida)
        const efficiencyClass = (branch.efficiency >= 85) ? 'kpi-cell-success' : (branch.efficiency >= 50) ? 'kpi-cell-warning' : 'kpi-cell-danger';
        const punctualityClass = (branch.punctuality >= 95) ? 'kpi-cell-success' : (branch.punctuality >= 70) ? 'kpi-cell-warning' : 'kpi-cell-danger';
        const sicClass = (branch.avgSIC >= 85) ? 'kpi-cell-success' : (branch.avgSIC >= 50) ? 'kpi-cell-warning' : 'kpi-cell-danger';

        tbody.innerHTML += `
            <tr>
                <td>${branch.name || 'N/A'}</td>
                <td>${branch.employees !== undefined ? branch.employees : 0}</td>
                <td class="${efficiencyClass}">${branch.efficiency !== undefined ? branch.efficiency.toFixed(1) : 'N/A'}%</td>
                <td class="${punctualityClass}">${branch.punctuality !== undefined ? branch.punctuality.toFixed(1) : 'N/A'}%</td>
                <td class="${sicClass}">${branch.avgSIC !== undefined ? branch.avgSIC.toFixed(1) : 'N/A'}</td>
                <td>${branch.absences !== undefined ? branch.absences : 0}</td>
            </tr>
        `;
    });

    // Añade la fila de totales/promedios
    const avgEfficiency = branches.length > 0 ? (sumEfficiency / branches.length).toFixed(1) : '0.0';
    const avgPunctuality = branches.length > 0 ? (sumPunctuality / branches.length).toFixed(1) : '0.0';
    const avgSic = branches.length > 0 ? (sumAvgSic / branches.length).toFixed(1) : '0.0';

    tbody.innerHTML += `
        <tr class="total-row">
            <td><strong>TOTAL / PROMEDIO</strong></td>
            <td><strong>${totalEmployees}</strong></td>
            <td><strong>${avgEfficiency}%</strong></td>
            <td><strong>${avgPunctuality}%</strong></td>
            <td><strong>${avgSic}</strong></td>
            <td><strong>${totalAbsences}</strong></td>
        </tr>
    `;
}

function updateEmployeeSummaryTable() {
    const tbody = document.getElementById('employeeSummaryTableBody');
    const searchInput = document.getElementById('employeeSearchInput');
    const searchTerm = searchInput.value.toLowerCase().trim();
    tbody.innerHTML = '';
    const colspanValue = 7;

    let employeeData = currentData?.employee_summary_kpis || [];

    if (searchTerm) {
        employeeData = employeeData.filter(emp => {
            const idMatch = String(emp.ID || '').toLowerCase().includes(searchTerm);
            const nameMatch = String(emp.Empleado || '').toLowerCase().includes(searchTerm);
            return idMatch || nameMatch;
        });
    }

    if (employeeData.length === 0) {
        const message = searchTerm ? 'No se encontraron empleados.' : 'No hay datos de resumen.';
        // --- CORRECCIÓN (Sintaxis) ---
        tbody.innerHTML = `<tr><td colspan="${colspanValue}" style="text-align:center;">${message}</td></tr>`;
        return;
    }

    employeeData.forEach(emp => {
        const hrsTrab = emp['Hrs. Trabajadas'] || '0:00:00';
        const hrsPlan = emp['Hrs. Planificadas'] || '0:00:00';
        const variacion = emp['Variación'] || '0:00:00';
        const retardos = emp.Retardos !== undefined ? emp.Retardos : 0;
        const ausencias = emp.Ausencias !== undefined ? emp.Ausencias : 0;

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

// --- FUNCIÓN DE TABLA KPI (Corregida) ---
function updateEmployeeKPITable() {
    const tbody = document.getElementById('employeeKpiTableBody');
    const searchInput = document.getElementById('employeeSearchInput');
    const searchTerm = searchInput.value.toLowerCase().trim();
    tbody.innerHTML = '';
    
    const colspanValue = 7; // ID, Nombre, Faltas Just, TasaAus, Punt, Efic, SIC

    let employeeData = currentData?.employee_performance_kpis || [];

    if (searchTerm) {
        employeeData = employeeData.filter(emp => {
            const idMatch = String(emp.ID || '').toLowerCase().includes(searchTerm);
            const nameMatch = String(emp.Nombre || '').toLowerCase().includes(searchTerm);
            return idMatch || nameMatch;
        });
    }

    if (employeeData.length === 0) {
        const message = searchTerm ? 'No se encontraron empleados.' : 'No hay datos de KPIs.';
        // --- CORRECCIÓN (Sintaxis) ---
        tbody.innerHTML = `<tr><td colspan="${colspanValue}" style="text-align:center;">${message}</td></tr>`;
        return;
    }

    function getKpiClass(value, kpiType) { 
        if (value === null || value === undefined || isNaN(value)) return ''; 
        
        switch (kpiType) { 
            case 'faltas_just': // Lógica: 0-5=Verde, 6-10=Amarillo, >10=Rojo
                return value <= 5 ? 'kpi-cell-success' : value <= 10 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            
            case 'ausentismo': 
                // --- CORRECCIÓN LÓGICA ---
                // Tasa de ausentismo (al revés): <5% (verde), <10% (amarillo), >=10% (rojo)
                return value <= 5 ? 'kpi-cell-success' : value < 10 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            
            case 'puntualidad': // >=95 (Verde), >=70 (Amarillo), <70 (Rojo)
                return value >= 95 ? 'kpi-cell-success' : value >= 70 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            
            case 'eficiencia': // >=85 (Verde), >=50 (Amarillo), <50 (Rojo)
                return value >= 85 ? 'kpi-cell-success' : value >= 50 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            
            case 'sic': // >=85 (Verde), >=50 (Amarillo), <50 (Rojo)
                return value >= 85 ? 'kpi-cell-success' : value >= 50 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            
            default: 
                return ''; 
        } 
    }

    employeeData.forEach(emp => {
        const faltasJustVal = emp['Faltas Justificadas'];
        const ausentismoVal = emp['Tasa Ausentismo (%)'];
        const puntualidadVal = emp['Índice Puntualidad (%)'];
        const eficienciaVal = emp['Eficiencia Horas (%)'];
        const sicVal = emp['SIC'];

        const faltasJustClass = getKpiClass(faltasJustVal, 'faltas_just');
        const ausentismoClass = getKpiClass(ausentismoVal, 'ausentismo');
        const puntualidadClass = getKpiClass(puntualidadVal, 'puntualidad');
        const eficienciaClass = getKpiClass(eficienciaVal, 'eficiencia');
        const sicClass = getKpiClass(sicVal, 'sic');

        const faltasJustStr = (faltasJustVal !== undefined && faltasJustVal !== null) ? faltasJustVal : '0';
        const ausentismoStr = ausentismoVal !== undefined ? ausentismoVal.toFixed(1) + '%' : 'N/A';
        const eficienciaStr = eficienciaVal !== undefined ? eficienciaVal.toFixed(1) + '%' : 'N/A';
        const puntualidadStr = puntualidadVal !== undefined ? puntualidadVal.toFixed(1) + '%' : 'N/A';
        const sicStr = sicVal !== undefined ? sicVal.toFixed(1) : 'N/A';

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
// --- FIN DE LA ACTUALIZACIÓN ---

function handleSearch() {
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
    // --- CORRECCIÓN (Sintaxis) ---
    noDataMsgElement.innerHTML = `
        <i class="fa-solid fa-info-circle" style="font-size: 50px; margin-bottom: 20px; color: var(--info-color);"></i>
        <h2>No hay datos disponibles</h2>
        <p>No se encontraron registros.</p>`;
    noDataMsgElement.style.display = 'block';
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('dashboardContent').style.display = 'block';
    document.getElementById('exportExcelBtn').disabled = true;
    
    // Asegurarse de que las tablas existan antes de limpiarlas
    const summaryTableBody = document.getElementById('summaryTableBody');
    // --- CORRECCIÓN (Sintaxis) ---
    if (summaryTableBody) summaryTableBody.innerHTML = `<tr><td colspan="6" style="text-align:center;">No hay datos.</td></tr>`;
    
    const employeeSummaryTableBody = document.getElementById('employeeSummaryTableBody');
    // --- CORRECCIÓN (Sintaxis) ---
    if (employeeSummaryTableBody) employeeSummaryTableBody.innerHTML = `<tr><td colspan="7" style="text-align:center;">No hay datos.</td></tr>`;
    
    const employeeKpiTableBody = document.getElementById('employeeKpiTableBody');
    // --- CORRECCIÓN (Sintaxis) ---
    if (employeeKpiTableBody) employeeKpiTableBody.innerHTML = `<tr><td colspan="7" style="text-align:center;">No hay datos.</td></tr>`;
    
    Object.values(charts).forEach(chart => {
        chart.data.labels = [];
        chart.data.datasets = [];
        chart.update();
    });
}

function showErrorState(title, message) {
    const noData = document.getElementById('noDataMessage');
    // --- CORRECCIÓN (Sintaxis) ---
    noData.innerHTML = `
        <i class="fa-solid fa-exclamation-triangle" style="font-size: 50px; margin-bottom: 20px; color: var(--danger-color);"></i>
        <h2>${title}</h2>
        <p>${message}</p>`;
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
    // --- FILTRO: Excluir "Rio Blanco" ---
    const allBranches = data?.branches || [];
    const branches = allBranches.filter(b => b.name && b.name.toLowerCase() !== 'rio blanco');
    
    const summary = data?.period_summary || {
        total_attendances: 0,
        total_permissions: 0,
        total_absences: 0,
        total_justified_absences: 0
    };
    const color = (variable) => getComputedStyle(document.documentElement).getPropertyValue(variable).trim();

    // --- Gráfica 1: Eficiencia por Sucursal (Corregida) ---
    charts.branchEfficiencyChart.data = {
        labels: branches.map(b => b.name || 'N/A'),
        datasets: [{
            data: branches.map(b => b.efficiency || 0),
            backgroundColor: branches.map(b => { // Colores dinámicos por valor
                const efficiency = b.efficiency || 0;
                if (efficiency >= 85) return color('--success-color');
                if (efficiency >= 50) return color('--warning-color');
                return color('--danger-color');
            })
        }]
    };

    // --- Gráfica 2: Distribución de SIC (Corregida) ---
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
        else if (sic >= 70) sicRanges['Bueno (70-84)']++; // Rango ajustado
        else if (sic >= 50) sicRanges['Regular (50-69)']++; // Rango ajustado
        else sicRanges['Crítico (<50)']++;
    });

    charts.sicDistributionChart.data = {
        labels: Object.keys(sicRanges),
        datasets: [{
            data: Object.values(sicRanges),
            backgroundColor: [
                color('--success-color'), // Excelente
                color('--info-color'),     // Bueno
                color('--warning-color'), // Regular
                color('--danger-color')   // Crítico
            ]
        }]
    };
    // FIN DE LA GRÁFICA SIC AJUSTADA

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

    // --- Gráfica 4: Top Empleados por Eficiencia (Corregida) ---
    const topEmployees = [...kpiData].sort((a, b) => (b['Eficiencia Horas (%)'] || 0) - (a['Eficiencia Horas (%)'] || 0)).slice(0, 10);
    const efficiencyColors = topEmployees.map(emp => {
        const eficiencia = emp['Eficiencia Horas (%)'] || 0;
        if (eficiencia >= 85) return color('--success-color');
        if (eficiencia >= 50) return color('--warning-color');
        return color('--danger-color');
    });

    charts.topEfficiencyChart.data = {
        labels: topEmployees.map(b => b.Nombre || 'N/A'),
        datasets: [{
            data: topEmployees.map(b => b['Eficiencia Horas (%)'] || 0),
            backgroundColor: efficiencyColors // Colores dinámicos
        }]
    };

    // --- Gráfica 5: Comparativa (Radar) (Corregida) ---
    const radarLabels = ['Eficiencia', 'Puntualidad', 'SIC', 'Productividad'];
    
    // Paleta de colores para el radar
    const dynamicColors = [
        'rgba(133, 30, 35, 0.6)',   // Rojo Oscuro (Principal)
        'rgba(59, 130, 246, 0.6)',  // Azul (Info)
        'rgba(22, 163, 74, 0.6)',   // Verde (Success)
        'rgba(245, 158, 11, 0.6)',  // Naranja (Warning)
        'rgba(155, 89, 182, 0.6)',  // Morado
    ];

    charts.branchComparisonChart.data = {
        labels: radarLabels,
        // Usar las sucursales ya filtradas (sin Rio Blanco)
        datasets: branches.map((b, i) => {
            const datasetColor = dynamicColors[i % dynamicColors.length]; // Asigna un color del array
            const borderColor = datasetColor.replace('0.6', '1'); 
            
            return {
                // --- CORRECCIÓN (Sintaxis) ---
                label: b.name || `Sucursal ${i+1}`,
                data: [b.efficiency || 0, b.punctuality || 0, b.avgSIC || 0, b.productivity || 0], // 'productivity' viene del backend
                backgroundColor: datasetColor,
                borderColor: borderColor,
                borderWidth: 2
            };
        })
    };

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

    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    // --- CORRECCIÓN (Sintaxis) ---
    const filename = `Dashboard_General_Analisis_${startDate}_a_${endDate}.xlsx`; // Nombre de archivo actualizado

    try {
        const response = await fetch('/api/export_dashboard_excel/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(currentData)
        });

        if (!response.ok) {
            // --- CORRECCIÓN (Sintaxis) ---
            let errorMsg = `Error ${response.status}`;
            try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorMsg;
            } catch(e) {
                errorMsg = await response.text();
            }
            throw new Error(errorMsg);
        }

        const blob = await response.blob();
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        setTimeout(() => {
            window.URL.revokeObjectURL(url);
            if (document.body.contains(a)) {
                document.body.removeChild(a);
            }
        }, 100);

    } catch (error) {
        console.error('Error al exportar Excel:', error);
        alert('Error al generar el archivo: ' + error.message);
    } finally {
        btn.innerHTML = '<i class="fa-solid fa-file-excel"></i> Exportar a Excel';
        btn.disabled = false;
    }
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