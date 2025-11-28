// Variables globales
let charts = {};
let currentData = null; // Guarda toda la data: { branches: [], period_summary: {}, employee_summary_kpis: [], employee_performance_kpis: [] }
let activeTab = 'summary'; // Pestaña activa por defecto ('summary' o 'kpis')

// --- INICIALIZACIÓN ---
document.addEventListener('DOMContentLoaded', () => {
    // Nota: Es mejor definir las variables CSS de color directamente en el CSS
    // para que getComputedStyle funcione correctamente.
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
    // Detiene el timeout anterior y crea uno nuevo para evitar múltiples llamadas rápidas
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
        
        // Calcular y aplicar el rango si no es personalizado
        const dates = calculateDateRange(range);
        document.getElementById('startDate').value = dates.startDate; 
        document.getElementById('endDate').value = dates.endDate;
        
        applyFiltersAutomatically();
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
            // "Este Mes" (del 1ro a hoy)
            startDate = new Date(today.getFullYear(), today.getMonth(), 1);
            endDate = new Date(today);
            break;
        case 'quarter':
            const quarter = Math.floor(today.getMonth() / 3);
            startDate = new Date(today.getFullYear(), quarter * 3, 1);
            // El último día del trimestre (Mes 3, 6, 9, 12)
            endDate = new Date(today.getFullYear(), quarter * 3 + 3, 0); 
            break;
        case 'year':
            startDate = new Date(today.getFullYear(), 0, 1);
            endDate = new Date(today.getFullYear(), 11, 31);
            break;
        default:
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

// --- LLAMADA A LA API ---
async function fetchDashboardData(startDate, endDate) {
    const apiUrl = `/api/dashboard/general/?startDate=${startDate}&endDate=${endDate}`;

    try {
        const response = await fetch(apiUrl);
        if (!response.ok) {
            let errorMessage = `Error ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) { /* Ignora */ }
            throw new Error(errorMessage);
        }
        const result = await response.json();
        if (!result.success) {
            throw new Error(result.error || 'Error desconocido reportado por la API');
        }
        
        const defaultData = {
            branches: [], period_summary: { total_attendances: 0, total_permissions: 0, total_absences: 0, total_justified_absences: 0 },
            employee_summary_kpis: [], employee_performance_kpis: []
        };
        const receivedData = result.data || {};

        return {
             branches: receivedData.branches || [],
             period_summary: receivedData.period_summary || defaultData.period_summary,
             employee_summary_kpis: receivedData.employee_summary_kpis || [],
             employee_performance_kpis: receivedData.employee_performance_kpis || []
        };
    } catch (error) {
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
    updateBranchesTable(data);
    handleSearch();
}

function updateMainKPIs(data) {
    // FILTRO: Excluir "Rio Blanco" del cálculo principal de KPI (si es necesario)
    const branches = (data?.branches || []).filter(b => b.name && b.name.toLowerCase() !== 'rio blanco');
    
    const totalEmployees = branches.reduce((sum, b) => sum + (b?.employees || 0), 0);
    const avgEfficiency = branches.length > 0 ? branches.reduce((sum, b) => sum + (b?.efficiency || 0), 0) / branches.length : 0;
    const avgPunctuality = branches.length > 0 ? branches.reduce((sum, b) => sum + (b?.punctuality || 0), 0) / branches.length : 0;
    const totalAbsences = data?.period_summary?.total_absences || 0;
    
    document.getElementById('totalEmployees').textContent = totalEmployees.toLocaleString();
    document.getElementById('avgEfficiency').textContent = `${avgEfficiency.toFixed(1)}%`;
    document.getElementById('avgPunctuality').textContent = `${avgPunctuality.toFixed(1)}%`;
    document.getElementById('totalAbsences').textContent = totalAbsences.toLocaleString();
}

// --- FUNCIÓN DE TABLA DE SUCURSALES ---
function updateBranchesTable(data) {
    const tbody = document.getElementById('summaryTableBody');
    if (!tbody) return; 
    
    tbody.innerHTML = '';
    // FILTRO: Excluir "Rio Blanco" y "Sin Asignar" de la tabla de resumen de sucursales
    const branches = (data?.branches || []).filter(b => 
        b.name && b.name.toLowerCase() !== 'rio blanco' && b.name !== 'Sin Asignar'
    );

    if (branches.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No hay datos de sucursales activas.</td></tr>';
        return;
    }

    let totalEmployees = 0;
    let sumEfficiency = 0;
    let sumPunctuality = 0;
    let sumAvgSic = 0;
    let totalAbsences = 0;
    
    // Obtener colores del CSS (Asumiendo que has definido las variables --success-color, etc.)
    const getColorClass = (value, minGood, minWarning) => {
        if (value >= minGood) return 'kpi-cell-success';
        if (value >= minWarning) return 'kpi-cell-warning';
        return 'kpi-cell-danger';
    };

    branches.forEach(branch => {
        totalEmployees += branch.employees || 0;
        sumEfficiency += branch.efficiency || 0;
        sumPunctuality += branch.punctuality || 0;
        sumAvgSic += branch.avgSIC || 0;
        totalAbsences += branch.absences || 0;

        // Nota: Las clases kpi-cell-X deben estar definidas en tu CSS para dar color.
        const efficiencyClass = getColorClass(branch.efficiency, 85, 50);
        const punctualityClass = getColorClass(branch.punctuality, 95, 70);
        const sicClass = getColorClass(branch.avgSIC, 85, 50);
        
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

// --- FUNCIÓN DE BÚSQUEDA ---
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
            const nameMatch = String(emp.Nombre || '').toLowerCase().includes(searchTerm);
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
        const ausencias = emp.Ausencias !== undefined ? emp.Ausencias : 0;

        tbody.innerHTML += `
            <tr>
                <td>${emp.ID || 'N/A'}</td>
                <td>${emp.Nombre || 'Sin Nombre'}</td>
                <td>${hrsTrab}</td>
                <td>${hrsPlan}</td>
                <td>${variacion}</td>
                <td>${retardos}</td>
                <td>${ausencias}</td>
            </tr>`;
    });
}

function updateEmployeeKPITable() {
    const tbody = document.getElementById('employeeKpiTableBody');
    const searchInput = document.getElementById('employeeSearchInput');
    const searchTerm = searchInput.value.toLowerCase().trim();
    tbody.innerHTML = '';
    
    const colspanValue = 7;

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
        tbody.innerHTML = `<tr><td colspan="${colspanValue}" style="text-align:center;">${message}</td></tr>`;
        return;
    }

    function getKpiClass(value, kpiType) { 
        if (value === null || value === undefined || isNaN(value)) return ''; 
        
        switch (kpiType) { 
            case 'faltas_just': 
                return value <= 5 ? 'kpi-cell-success' : value <= 10 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            case 'ausentismo': 
                return value <= 5 ? 'kpi-cell-success' : value < 10 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            case 'puntualidad': 
                return value >= 95 ? 'kpi-cell-success' : value >= 70 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            case 'eficiencia': 
                return value >= 85 ? 'kpi-cell-success' : value >= 50 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            case 'sic': 
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
    noDataMsgElement.innerHTML = `
        <i class="fa-solid fa-info-circle" style="font-size: 50px; margin-bottom: 20px; color: var(--info-color);"></i>
        <h2>No hay datos disponibles</h2>
        <p>No se encontraron registros.</p>`;
    noDataMsgElement.style.display = 'block';
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('dashboardContent').style.display = 'block';
    document.getElementById('exportExcelBtn').disabled = true;
    
    const summaryTableBody = document.getElementById('summaryTableBody');
    if (summaryTableBody) summaryTableBody.innerHTML = `<tr><td colspan="6" style="text-align:center;">No hay datos.</td></tr>`;
    
    const employeeSummaryTableBody = document.getElementById('employeeSummaryTableBody');
    if (employeeSummaryTableBody) employeeSummaryTableBody.innerHTML = `<tr><td colspan="7" style="text-align:center;">No hay datos.</td></tr>`;
    
    const employeeKpiTableBody = document.getElementById('employeeKpiTableBody');
    if (employeeKpiTableBody) employeeKpiTableBody.innerHTML = `<tr><td colspan="7" style="text-align:center;">No hay datos.</td></tr>`;
    
    Object.values(charts).forEach(chart => {
        chart.data.labels = [];
        chart.data.datasets = [];
        chart.update();
    });
}

function showErrorState(title, message) {
    const noData = document.getElementById('noDataMessage');
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

// --- FUNCIÓN DE GRÁFICAS (ACTUALIZADA Y CORREGIDA) ---
function updateAllCharts(data) {
    const allBranches = data?.branches || [];
    
    // 💥 FILTRADO CRUCIAL: Excluir 'Rio Blanco' y 'Sin Asignar' 💥
    const branches = allBranches.filter(b => 
        (b.name && b.name.toLowerCase() !== 'rio blanco') && 
        (b.name !== 'Sin Asignar') 
    );
    
    const summary = data?.period_summary || {
        total_attendances: 0, total_permissions: 0, total_absences: 0, total_justified_absences: 0
    };
    // Obtener color del CSS
    const color = (variable) => getComputedStyle(document.documentElement).getPropertyValue(variable).trim();

    // --- Gráfica 1: Eficiencia por Sucursal (Usando 'branches' filtrado) ---
    charts.branchEfficiencyChart.data = {
        labels: branches.map(b => b.name || 'N/A'),
        datasets: [{
            data: branches.map(b => b.efficiency || 0),
            backgroundColor: branches.map(b => { 
                const efficiency = b.efficiency || 0;
                if (efficiency >= 85) return color('--success-color');
                if (efficiency >= 50) return color('--warning-color');
                return color('--danger-color');
            })
        }]
    };

    // --- Gráfica 2: Distribución de SIC ---
    const sicRanges = {
        'Excelente (>=85)': 0, 'Bueno (70-84)': 0, 'Regular (50-69)': 0, 'Crítico (<50)': 0
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
            backgroundColor: [color('--success-color'), color('--info-color'), color('--warning-color'), color('--danger-color')]
        }]
    };

    // --- Gráfica 3: Eventos del Periodo ---
    charts.periodEventsChart.data = {
        labels: ['Asistencias', 'Permisos', 'Faltas', 'F. Justificadas'],
        datasets: [{
            data: [
                summary.total_attendances || 0, summary.total_permissions || 0, 
                summary.total_absences || 0, summary.total_justified_absences || 0
            ],
            backgroundColor: [color('--success-color'), color('--info-color'), color('--danger-color'), color('--warning-color')]
        }]
    };
    charts.periodEventsChart.options.scales.y.title.text = 'Total Ocurrencias';

    // --- Gráfica 4: Top Empleados por Eficiencia ---
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
            backgroundColor: efficiencyColors
        }]
    };

    // --- Gráfica 5: Comparativa (Radar) ---
    const radarLabels = ['Eficiencia', 'Puntualidad', 'SIC', 'Productividad'];
    const dynamicColors = [
        'rgba(133, 30, 35, 0.6)', 'rgba(59, 130, 246, 0.6)', 'rgba(22, 163, 74, 0.6)', 
        'rgba(245, 158, 11, 0.6)', 'rgba(155, 89, 182, 0.6)',
    ];

    charts.branchComparisonChart.data = {
        labels: radarLabels,
        datasets: branches.map((b, i) => { // Usamos 'branches' filtrado
            const datasetColor = dynamicColors[i % dynamicColors.length];
            const borderColor = datasetColor.replace('0.6', '1'); 
            
            return {
                label: b.name || `Sucursal ${i+1}`,
                data: [b.efficiency || 0, b.punctuality || 0, b.avgSIC || 0, b.productivity || 0],
                backgroundColor: datasetColor,
                borderColor: borderColor,
                borderWidth: 2
            };
        })
    };

    Object.values(charts).forEach(chart => chart.update());
}


// --- EXPORTACIÓN A EXCEL (LLAMA AL BACKEND CON POST) ---
// (Mantenemos tu función original de exportación)
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
    const filename = `Dashboard_General_Analisis_${startDate}_a_${endDate}.xlsx`;

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