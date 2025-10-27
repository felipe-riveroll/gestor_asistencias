// Variables globales
let charts = {};
let currentData = null;
let employeesTable = null;

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    initializeTabs();
    loadInitialData();
});

// Inicializar dashboard
function initializeDashboard() {
    // Configurar fecha por defecto (este mes)
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    
    document.getElementById('startDate').value = firstDay.toISOString().split('T')[0];
    document.getElementById('endDate').value = lastDay.toISOString().split('T')[0];
    
    // Event listeners
    document.getElementById('dateRange').addEventListener('change', handleDateRangeChange);
    document.getElementById('applyFiltersBtn').addEventListener('click', applyFilters);
    document.getElementById('exportExcelBtn').addEventListener('click', exportToExcel);
    document.getElementById('refreshTableBtn').addEventListener('click', loadInitialData);
    
    // Inicializar gráficas
    initializeCharts();
    
    // Inicializar DataTable
    initializeDataTable();
}

// Inicializar sistema de pestañas
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabId = this.getAttribute('data-tab');
            
            // Remover clase active de todos los botones y contenidos
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            // Agregar clase active al botón y contenido actual
            this.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        });
    });
}

// Manejar cambio de rango de fechas
function handleDateRangeChange() {
    const range = document.getElementById('dateRange').value;
    const customDates = document.querySelectorAll('.custom-dates');
    
    if (range === 'custom') {
        customDates.forEach(el => el.style.display = 'flex');
    } else {
        customDates.forEach(el => el.style.display = 'none');
    }
}

// Aplicar filtros
function applyFilters() {
    loadInitialData();
}

// Cargar datos iniciales
async function loadInitialData() {
    showLoadingState();
    
    try {
        const dateRange = document.getElementById('dateRange').value;
        let startDate, endDate;
        
        if (dateRange === 'custom') {
            startDate = document.getElementById('startDate').value;
            endDate = document.getElementById('endDate').value;
        } else {
            const dates = calculateDateRange(dateRange);
            startDate = dates.startDate;
            endDate = dates.endDate;
        }
        
        // Cargar datos de todas las sucursales
        currentData = await fetchAllBranchesData(startDate, endDate);
        
        if (currentData && currentData.branches && currentData.branches.length > 0) {
            updateDashboard(currentData);
        } else {
            showNoData();
        }
    } catch (error) {
        console.error('Error al cargar datos:', error);
        showError();
    }
}

// Calcular rango de fechas
function calculateDateRange(range) {
    const today = new Date();
    let startDate, endDate;
    
    switch(range) {
        case 'today':
            startDate = today.toISOString().split('T')[0];
            endDate = startDate;
            break;
        case 'week':
            const startOfWeek = new Date(today);
            startOfWeek.setDate(today.getDate() - today.getDay());
            startDate = startOfWeek.toISOString().split('T')[0];
            endDate = today.toISOString().split('T')[0];
            break;
        case 'month':
            startDate = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
            endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().split('T')[0];
            break;
        case 'quarter':
            const quarter = Math.floor(today.getMonth() / 3);
            startDate = new Date(today.getFullYear(), quarter * 3, 1).toISOString().split('T')[0];
            endDate = new Date(today.getFullYear(), quarter * 3 + 3, 0).toISOString().split('T')[0];
            break;
        case 'year':
            startDate = new Date(today.getFullYear(), 0, 1).toISOString().split('T')[0];
            endDate = new Date(today.getFullYear(), 11, 31).toISOString().split('T')[0];
            break;
        default:
            startDate = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
            endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().split('T')[0];
    }
    
    return { startDate, endDate };
}

// Función para obtener datos (REEMPLAZAR CON TU API)
async function fetchAllBranchesData(startDate, endDate) {
    console.log(`Cargando datos de ${startDate} a ${endDate}`);
    
    // 🎯 REEMPLAZA ESTO CON TU LLAMADA REAL A LA API
    /*
    const response = await fetch(`/api/dashboard/general?start=${startDate}&end=${endDate}`);
    if (!response.ok) throw new Error('Error en la API');
    return await response.json();
    */
    
    // Por ahora retorna null para mostrar estado sin datos
    return null;
}

// Inicializar gráficas
function initializeCharts() {
    const chartConfigs = {
        branchEfficiencyChart: {
            type: 'bar',
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: { display: true, text: 'Eficiencia (%)' }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        },
        sicDistributionChart: {
            type: 'doughnut',
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        },
        bradfordLevelsChart: {
            type: 'pie',
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        },
        topEfficiencyChart: {
            type: 'bar',
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 100,
                        title: { display: true, text: 'Eficiencia (%)' }
                    }
                }
            }
        },
        branchComparisonChart: {
            type: 'radar',
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        }
    };
    
    Object.keys(chartConfigs).forEach(chartId => {
        const ctx = document.getElementById(chartId).getContext('2d');
        const config = chartConfigs[chartId];
        
        charts[chartId] = new Chart(ctx, {
            type: config.type,
            data: { labels: [], datasets: [] },
            options: config.options
        });
    });
}

// Inicializar DataTable
function initializeDataTable() {
    employeesTable = new DataTable('#employeesTable', {
        dom: '<"dt-layout-row"<"dt-layout-cell"l><"dt-layout-cell"f>>t<"dt-layout-row"<"dt-layout-cell"i><"dt-layout-cell"p>>',
        language: {
            url: 'https://cdn.datatables.net/plug-ins/2.0.3/i18n/es-MX.json',
            search: '',
            searchPlaceholder: 'Buscar empleados...'
        },
        pageLength: 10,
        responsive: true
    });
}

// Mostrar estado de carga
function showLoadingState() {
    document.getElementById('loadingState').style.display = 'block';
    document.getElementById('noDataMessage').style.display = 'none';
    document.getElementById('dashboardContent').style.display = 'none';
    document.getElementById('exportExcelBtn').disabled = true;
}

// Mostrar estado sin datos
function showNoData() {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('noDataMessage').style.display = 'block';
    document.getElementById('dashboardContent').style.display = 'none';
    document.getElementById('exportExcelBtn').disabled = true;
}

// Mostrar error
function showError() {
    const noDataMessage = document.getElementById('noDataMessage');
    noDataMessage.innerHTML = `
        <i class="fa-solid fa-exclamation-triangle"></i>
        <h2>Error al cargar datos</h2>
        <p>Intenta nuevamente o verifica tu conexión</p>
    `;
    showNoData();
}

// Actualizar dashboard con datos
function updateDashboard(data) {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('noDataMessage').style.display = 'none';
    document.getElementById('dashboardContent').style.display = 'block';
    document.getElementById('exportExcelBtn').disabled = false;
    
    // Actualizar KPIs principales
    updateMainKPIs(data);
    
    // Actualizar gráficas
    updateCharts(data);
    
    // Actualizar tabla de empleados
    updateEmployeesTable(data);
}

// Actualizar KPIs principales
function updateMainKPIs(data) {
    const branches = data.branches || [];
    const totalEmployees = branches.reduce((sum, branch) => sum + (branch.employees || 0), 0);
    const avgEfficiency = branches.reduce((sum, branch) => sum + (branch.efficiency || 0), 0) / (branches.length || 1);
    const avgPunctuality = branches.reduce((sum, branch) => sum + (branch.punctuality || 0), 0) / (branches.length || 1);
    const totalAbsences = branches.reduce((sum, branch) => sum + (branch.absences || 0), 0);
    
    document.getElementById('totalEmployees').textContent = totalEmployees.toLocaleString();
    document.getElementById('avgEfficiency').textContent = `${avgEfficiency.toFixed(1)}%`;
    document.getElementById('avgPunctuality').textContent = `${avgPunctuality.toFixed(1)}%`;
    document.getElementById('totalAbsences').textContent = totalAbsences.toLocaleString();
}

// Actualizar gráficas
function updateCharts(data) {
    const branches = data.branches || [];
    
    // Gráfica de eficiencia por sucursal
    updateBranchEfficiencyChart(branches);
    
    // Gráfica de distribución SIC
    updateSICDistributionChart(branches);
    
    // Gráfica de niveles Bradford
    updateBradfordLevelsChart(branches);
    
    // Gráfica top eficiencia
    updateTopEfficiencyChart(branches);
    
    // Gráfica comparativa
    updateBranchComparisonChart(branches);
}

// Actualizar gráficas individuales
function updateBranchEfficiencyChart(branches) {
    const labels = branches.map(branch => branch.name);
    const efficiencies = branches.map(branch => branch.efficiency);
    
    charts.branchEfficiencyChart.data = {
        labels: labels,
        datasets: [{
            label: 'Eficiencia (%)',
            data: efficiencies,
            backgroundColor: '#851E23',
            borderColor: '#a4494d',
            borderWidth: 1
        }]
    };
    charts.branchEfficiencyChart.update();
}

function updateSICDistributionChart(branches) {
    const sicRanges = { 'Excelente (>85)': 0, 'Bueno (70-85)': 0, 'Regular (50-70)': 0, 'Crítico (<50)': 0 };
    
    branches.forEach(branch => {
        const sic = branch.avgSIC || 0;
        if (sic > 85) sicRanges['Excelente (>85)']++;
        else if (sic >= 70) sicRanges['Bueno (70-85)']++;
        else if (sic >= 50) sicRanges['Regular (50-70)']++;
        else sicRanges['Crítico (<50)']++;
    });
    
    charts.sicDistributionChart.data = {
        labels: Object.keys(sicRanges),
        datasets: [{
            data: Object.values(sicRanges),
            backgroundColor: ['#16a34a', '#f59e0b', '#ef4444', '#6b7280']
        }]
    };
    charts.sicDistributionChart.update();
}

function updateBradfordLevelsChart(branches) {
    const bradfordLevels = { 'Excelente (0-25)': 0, 'Bueno (26-50)': 0, 'Regular (51-100)': 0, 'Crítico (>100)': 0 };
    
    branches.forEach(branch => {
        const bradford = branch.avgBradford || 0;
        if (bradford <= 25) bradfordLevels['Excelente (0-25)']++;
        else if (bradford <= 50) bradfordLevels['Bueno (26-50)']++;
        else if (bradford <= 100) bradfordLevels['Regular (51-100)']++;
        else bradfordLevels['Crítico (>100)']++;
    });
    
    charts.bradfordLevelsChart.data = {
        labels: Object.keys(bradfordLevels),
        datasets: [{
            data: Object.values(bradfordLevels),
            backgroundColor: ['#16a34a', '#f59e0b', '#ef4444', '#6b7280']
        }]
    };
    charts.bradfordLevelsChart.update();
}

function updateTopEfficiencyChart(branches) {
    const sortedBranches = [...branches].sort((a, b) => (b.efficiency || 0) - (a.efficiency || 0)).slice(0, 10);
    
    charts.topEfficiencyChart.data = {
        labels: sortedBranches.map(branch => branch.name),
        datasets: [{
            label: 'Eficiencia (%)',
            data: sortedBranches.map(branch => branch.efficiency),
            backgroundColor: '#3b82f6'
        }]
    };
    charts.topEfficiencyChart.update();
}

function updateBranchComparisonChart(branches) {
    const labels = ['Eficiencia', 'Puntualidad', 'SIC', 'Productividad'];
    const topBranches = branches.slice(0, 5);
    
    charts.branchComparisonChart.data = {
        labels: labels,
        datasets: topBranches.map((branch, index) => ({
            label: branch.name,
            data: [
                branch.efficiency || 0,
                branch.punctuality || 0,
                branch.avgSIC || 0,
                branch.productivity || 0
            ],
            backgroundColor: `rgba(${133 + index * 20}, ${30 + index * 10}, ${35 + index * 5}, 0.2)`,
            borderColor: `rgb(${133 + index * 20}, ${30 + index * 10}, ${35 + index * 5})`,
            borderWidth: 1
        }))
    };
    charts.branchComparisonChart.update();
}

// Actualizar tabla de empleados
function updateEmployeesTable(data) {
    const employees = data.employees || [];
    
    if (employeesTable) {
        employeesTable.clear();
        
        employees.forEach(emp => {
            employeesTable.row.add([
                emp.id || '',
                emp.name || '',
                emp.branch || '',
                `${(emp.efficiency || 0).toFixed(1)}%`,
                `${(emp.punctuality || 0).toFixed(1)}%`,
                emp.bradford || 0,
                (emp.sic || 0).toFixed(1),
                emp.absences || 0
            ]);
        });
        
        employeesTable.draw();
    }
}

// Exportar a Excel
function exportToExcel() {
    if (!currentData || !currentData.branches || currentData.branches.length === 0) {
        alert('No hay datos para exportar.');
        return;
    }
    
    const btn = document.getElementById('exportExcelBtn');
    const originalHtml = btn.innerHTML;
    
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    btn.disabled = true;
    
    try {
        // Preparar datos para Excel
        const excelData = currentData.branches.map(branch => ({
            'Sucursal': branch.name,
            'Empleados': branch.employees || 0,
            'Eficiencia (%)': branch.efficiency || 0,
            'Puntualidad (%)': branch.punctuality || 0,
            'Bradford Promedio': branch.avgBradford || 0,
            'SIC Promedio': branch.avgSIC || 0,
            'Ausencias': branch.absences || 0
        }));
        
        // Agregar totales
        const totals = {
            'Sucursal': 'TOTALES',
            'Empleados': currentData.branches.reduce((sum, b) => sum + (b.employees || 0), 0),
            'Eficiencia (%)': currentData.branches.reduce((sum, b) => sum + (b.efficiency || 0), 0) / currentData.branches.length,
            'Puntualidad (%)': currentData.branches.reduce((sum, b) => sum + (b.punctuality || 0), 0) / currentData.branches.length,
            'Bradford Promedio': currentData.branches.reduce((sum, b) => sum + (b.avgBradford || 0), 0) / currentData.branches.length,
            'SIC Promedio': currentData.branches.reduce((sum, b) => sum + (b.avgSIC || 0), 0) / currentData.branches.length,
            'Ausencias': currentData.branches.reduce((sum, b) => sum + (b.absences || 0), 0)
        };
        excelData.push(totals);
        
        // Crear hoja de trabajo
        const ws = XLSX.utils.json_to_sheet(excelData);
        
        // Ajustar anchos de columnas
        ws['!cols'] = [
            { wch: 20 }, { wch: 12 }, { wch: 15 }, 
            { wch: 15 }, { wch: 18 }, { wch: 15 }, { wch: 12 }
        ];
        
        // Crear libro y descargar
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "Resumen General");
        XLSX.writeFile(wb, `Dashboard_General_${new Date().toISOString().split('T')[0]}.xlsx`);
        
    } catch (error) {
        console.error('Error al exportar:', error);
        alert('Error al exportar el archivo.');
    } finally {
        setTimeout(() => {
            btn.innerHTML = originalHtml;
            btn.disabled = false;
        }, 1000);
    }
}