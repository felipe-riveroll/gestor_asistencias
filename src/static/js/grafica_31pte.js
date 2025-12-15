// ==========================================
// GRAFICA_31PTE.JS - VERSIÓN OPTIMIZADA
// ==========================================

// --- VARIABLES GLOBALES ---
let charts = {};
let currentData = null; // Guardará toda la data
let activeTab = 'summary'; // Pestaña activa por defecto

// --- INICIALIZACIÓN ---
document.addEventListener('DOMContentLoaded', () => {
    // Solo iniciamos el dashboard una vez que el DOM esté listo
    initializeDashboard();
});

function initializeDashboard() {
    console.log("🚀 Iniciando Dashboard 31PTE...");

    // 1. Obtener referencias a elementos
    const dateRangeSelect = document.getElementById('dateRange');
    const startInput = document.getElementById('startDate');
    const endInput = document.getElementById('endDate');

    // 2. CONFIGURACIÓN INICIAL SEGURA (CRÍTICO PARA EVITAR CRASH)
    // Forzamos el valor 'month' en el select para evitar que se quede pegado en 'year' por caché
    if (dateRangeSelect) {
        dateRangeSelect.value = 'month';
    }

    // 3. CALCULAR FECHAS (ÚLTIMOS 30 DÍAS)
    // Esto asegura una carga ligera al inicio
    const { startDate, endDate } = calculateDateRange('month');

    // 4. ASIGNAR FECHAS A LOS INPUTS (SILENCIOSAMENTE)
    if (startInput) startInput.value = startDate;
    if (endInput) endInput.value = endDate;

    // 5. CONFIGURAR LISTENERS
    // Los configuramos DESPUÉS de poner los valores para que no se disparen eventos falsos
    if (dateRangeSelect) dateRangeSelect.addEventListener('change', handleDateRangeChange);
    if (startInput) startInput.addEventListener('change', applyFiltersAutomatically);
    if (endInput) endInput.addEventListener('change', applyFiltersAutomatically);

    // Listener Exportar Excel
    const exportBtn = document.getElementById('exportExcelBtn');
    if (exportBtn) exportBtn.addEventListener('click', exportToExcelWithStyles);

    // Listener Buscador
    const searchInput = document.getElementById('employeeSearchInput');
    if (searchInput) searchInput.addEventListener('input', handleSearch);

    // Listeners para Pestañas
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', function() {
            // Cambiar pestaña activa visualmente
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            this.classList.add('active');
            
            // Actualizar lógica interna
            activeTab = this.getAttribute('data-tab');
            const content = document.getElementById(activeTab);
            if (content) content.classList.add('active');

            // Refrescar la tabla AHORA visible con el filtro actual
            handleSearch();
        });
    });

    // Activar la primera pestaña por defecto
    const defaultTab = document.querySelector('.tab-button[data-tab="summary"]');
    if (defaultTab) {
        defaultTab.classList.add('active');
        document.getElementById('summary').classList.add('active');
    }

    // 6. INICIALIZAR GRÁFICAS VACÍAS
    initializeCharts(); 

    // 7. CARGA DE DATOS INICIAL (UNA SOLA VEZ)
    console.log(`📅 Carga inicial: ${startDate} al ${endDate}`);
    loadInitialData(); 
}

// --- MANEJO DE FECHAS ---
function calculateDateRange(range) {
    const today = new Date();
    let startDate = new Date(today);
    let endDate = new Date(today);

    switch(range) { 
        case 'today': 
            break; 
        case 'week': 
            const dayOfWeek = today.getDay();
            const diff = today.getDate() - dayOfWeek + (dayOfWeek === 0 ? -6 : 1);
            startDate = new Date(today.getFullYear(), today.getMonth(), diff);
            break; 
        
        case 'month': 
            // Lógica: 1 Mes exacto hacia atrás (Ej: 12 Nov a 12 Dic)
            startDate.setMonth(startDate.getMonth() - 1); 
            break; 

        case 'quarter': 
            // Trimestre actual
            const quarter = Math.floor(today.getMonth() / 3);
            startDate = new Date(today.getFullYear(), quarter * 3, 1);
            endDate = new Date(today.getFullYear(), quarter * 3 + 3, 0);
            break; 
            
        case 'year': 
            // Año completo (1 Enero a 31 Dic)
            startDate = new Date(today.getFullYear(), 0, 1);
            endDate = new Date(today.getFullYear(), 11, 31);
            break; 
            
        default: 
            // Default seguro: 1 mes atrás
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

// Llama a loadInitialData con retraso (Debounce)
function applyFiltersAutomatically() {
    clearTimeout(window.filterTimeout);
    window.filterTimeout = setTimeout(loadInitialData, 500); // Aumentado a 500ms para seguridad
}

// Muestra/oculta inputs de fecha personalizada
function handleDateRangeChange() {
    const range = document.getElementById('dateRange').value;
    const customDatesWrapper = document.querySelector('.custom-dates-wrapper');
    
    if (range === 'custom') {
        if (customDatesWrapper) customDatesWrapper.style.display = 'flex';
    } else {
        if (customDatesWrapper) customDatesWrapper.style.display = 'none';
        
        // Recalcular fechas y actualizar inputs
        const dates = calculateDateRange(range);
        document.getElementById('startDate').value = dates.startDate;
        document.getElementById('endDate').value = dates.endDate;
        
        applyFiltersAutomatically(); 
    }
}

// --- CARGA DE DATOS (CORE) ---
async function loadInitialData() {
    showLoadingState();
    
    try {
        const dateRangeSelect = document.getElementById('dateRange');
        let startDate = document.getElementById('startDate').value;
        let endDate = document.getElementById('endDate').value;

        // Validación básica
        if (!startDate || !endDate) { 
            showErrorState('Fechas Incompletas', 'Selecciona fecha de inicio y fin.'); 
            return; 
        }
        if (new Date(startDate) > new Date(endDate)) { 
            showErrorState('Fechas Inválidas', 'La fecha de inicio no puede ser posterior a la fecha de fin.'); 
            return; 
        }

        // LLAMADA A LA API
        const apiResponse = await fetchAllBranchesData(startDate, endDate); 

        // Verificación de datos
        if (apiResponse && typeof apiResponse === 'object') {
             currentData = apiResponse; // Guardar en variable global

            // Verificar si hay datos reales
            const hasData = (apiResponse.branches && apiResponse.branches.length > 0) || 
                            (apiResponse.employee_summary_kpis && apiResponse.employee_summary_kpis.length > 0);

            if (hasData) {
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

async function fetchAllBranchesData(startDate, endDate) {
    console.log(`📡 Cargando datos de 31PTE de ${startDate} a ${endDate}...`);
    
    // Construcción limpia de la URL
    const apiUrl = `/api/dashboard/31pte/?startDate=${startDate}&endDate=${endDate}`;
    
    try {
        const response = await fetch(apiUrl);
        
        if (!response.ok) { 
            let errorMessage = `Error ${response.status}: ${response.statusText}`; 
            try { 
                const errorData = await response.json(); 
                errorMessage = errorData?.error || errorMessage; 
            } catch (e) { /* Ignora error de parseo */ } 
            throw new Error(errorMessage); 
        }

        const result = await response.json();
        
        if (!result.success) { 
            throw new Error(result.error || 'Error desconocido reportado por la API'); 
        }

        console.log("✅ Datos recibidos:", result.data);

        // Estructura por defecto para evitar undefined
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
        console.error('Falló fetchAllBranchesData:', error); 
        throw error; 
    }
}

// --- ACTUALIZACIÓN DE UI ---
function updateDashboard(data) {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('noDataMessage').style.display = 'none';
    document.getElementById('dashboardContent').style.display = 'block';
    
    const exportBtn = document.getElementById('exportExcelBtn');
    if (exportBtn) exportBtn.disabled = false;
    
    updateMainKPIs(data);
    updateAllCharts(data);
    handleSearch(); // Actualiza la tabla activa
}

function updateMainKPIs(data) {
    const branches = data?.branches || [];
    
    // Cálculos seguros
    const totalEmployees = branches.reduce((sum, b) => sum + (b?.employees || 0), 0);
    const avgEfficiency = branches.length > 0 ? branches.reduce((sum, b) => sum + (b?.efficiency || 0), 0) / branches.length : 0;
    const avgPunctuality = branches.length > 0 ? branches.reduce((sum, b) => sum + (b?.punctuality || 0), 0) / branches.length : 0;
    const totalAbsences = data?.period_summary?.total_absences || 0; 

    // Actualizar DOM
    const elTotal = document.getElementById('totalEmployees');
    if(elTotal) elTotal.textContent = totalEmployees.toLocaleString();

    const elEff = document.getElementById('avgEfficiency');
    if(elEff) elEff.textContent = `${avgEfficiency.toFixed(1)}%`;

    const elPunc = document.getElementById('avgPunctuality');
    if(elPunc) elPunc.textContent = `${avgPunctuality.toFixed(1)}%`;

    const elAbs = document.getElementById('totalAbsences');
    if(elAbs) elAbs.textContent = totalAbsences.toLocaleString();
}

// --- TABLA 1: RESUMEN HORAS ---
function updateEmployeeSummaryTable() {
    const tbody = document.getElementById('employeeSummaryTableBody');
    if (!tbody) return;

    const searchInput = document.getElementById('employeeSearchInput');
    const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : '';
    
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

// --- TABLA 2: KPIS RENDIMIENTO (Con Colores) ---
function updateEmployeeKPITable() {
    const tbody = document.getElementById('employeeKpiTableBody');
    if (!tbody) return;

    const searchInput = document.getElementById('employeeSearchInput');
    const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : '';
    
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

    // Lógica de colores (Semáforo)
    function getKpiClass(value, kpiType) { 
        if (value === null || value === undefined || isNaN(value)) return ''; 
        
        switch (kpiType) { 
            case 'faltas_just': 
                return value <= 5 ? 'kpi-cell-success' : value <= 10 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            case 'ausentismo': 
                return value >= 95 ? 'kpi-cell-success' : value >= 70 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            case 'puntualidad': 
                return value >= 95 ? 'kpi-cell-success' : value >= 70 ? 'kpi-cell-warning' : 'kpi-cell-danger'; 
            case 'eficiencia': 
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

        const faltasJustStr = (faltasJustVal !== undefined) ? faltasJustVal : '0';
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

// --- BUSCADOR CENTRALIZADO ---
function handleSearch() {
    if (activeTab === 'summary') {
        updateEmployeeSummaryTable();
    } else if (activeTab === 'kpis') {
        updateEmployeeKPITable();
    }
}

// --- ESTADOS DE UI ---
function showLoadingState() { 
    const loading = document.getElementById('loadingState');
    if(loading) loading.style.display = 'block'; 
    
    document.getElementById('noDataMessage').style.display = 'none'; 
    document.getElementById('dashboardContent').style.display = 'none'; 
    
    const exportBtn = document.getElementById('exportExcelBtn');
    if(exportBtn) exportBtn.disabled = true; 
}

function showNoData() { 
    const noDataMsgElement = document.getElementById('noDataMessage'); 
    noDataMsgElement.innerHTML = `
        <i class="fa-solid fa-info-circle" style="font-size: 50px; margin-bottom: 20px; color: var(--info-color);"></i>
        <h2>No hay datos disponibles</h2>
        <p>No se encontraron registros para este periodo.</p>`; 
    noDataMsgElement.style.display = 'block'; 

    document.getElementById('loadingState').style.display = 'none'; 
    document.getElementById('dashboardContent').style.display = 'block'; 
    
    // Deshabilitar Excel si no hay datos
    const exportBtn = document.getElementById('exportExcelBtn');
    if(exportBtn) exportBtn.disabled = true; 

    // Limpia tablas
    const summaryTbody = document.getElementById('employeeSummaryTableBody');
    if(summaryTbody) summaryTbody.innerHTML = `<tr><td colspan="7" style="text-align:center;">No hay datos.</td></tr>`; 
    
    const kpiTbody = document.getElementById('employeeKpiTableBody');
    if(kpiTbody) kpiTbody.innerHTML = `<tr><td colspan="7" style="text-align:center;">No hay datos.</td></tr>`; 

    // Limpia Gráficas
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
    noData.style.display = 'block'; 
    
    document.getElementById('loadingState').style.display = 'none'; 
    document.getElementById('dashboardContent').style.display = 'none'; 
    
    const exportBtn = document.getElementById('exportExcelBtn');
    if(exportBtn) exportBtn.disabled = true; 
}

// --- CHART.JS ---
function initializeCharts() { 
    const commonOptions = { responsive: true, maintainAspectRatio: false }; 

    // 1. Eficiencia Sucursal
    if(document.getElementById('branchEfficiencyChart')) {
        charts.branchEfficiencyChart = new Chart('branchEfficiencyChart', { 
            type: 'bar', 
            options: { ...commonOptions, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } } 
        }); 
    }

    // 2. SIC Distribution
    if(document.getElementById('sicDistributionChart')) {
        charts.sicDistributionChart = new Chart('sicDistributionChart', { 
            type: 'doughnut', 
            options: { ...commonOptions, plugins: { legend: { position: 'bottom' } } } 
        }); 
    }

    // 3. Eventos Periodo
    if(document.getElementById('periodEventsChart')) {
        charts.periodEventsChart = new Chart('periodEventsChart', { 
            type: 'bar', 
            options: { ...commonOptions, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, title: { display: true, text: 'Ocurrencias' } } } } 
        }); 
    }

    // 4. Top Eficiencia
    if(document.getElementById('topEfficiencyChart')) {
        charts.topEfficiencyChart = new Chart('topEfficiencyChart', { 
            type: 'bar', 
            options: { ...commonOptions, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, max: 100 } } } 
        }); 
    }

    // 5. Radar Comparativo
    if(document.getElementById('branchComparisonChart')) {
        charts.branchComparisonChart = new Chart('branchComparisonChart', { 
            type: 'radar', 
            options: { ...commonOptions, scales: { r: { beginAtZero: true, max: 100 } } } 
        }); 
    }
}

function updateAllCharts(data) { 
    const branches = data?.branches || []; 
    const summary = data?.period_summary || { total_attendances: 0, total_permissions: 0, total_absences: 0, total_justified_absences: 0 }; 
    const color = (variable) => getComputedStyle(document.documentElement).getPropertyValue(variable).trim(); 

    // --- Gráfica 1: Eficiencia (31PTE) ---
    if(charts.branchEfficiencyChart) {
        charts.branchEfficiencyChart.data = { 
            labels: branches.map(b => b.name || 'N/A'), 
            datasets: [{ 
                data: branches.map(b => b.efficiency || 0), 
                backgroundColor: color('--primary-color') 
            }] 
        }; 
    }

    // --- Gráfica 2: Distribución SIC ---
    const sicRanges = { 'Excelente (>=85)': 0, 'Bueno (70-84)': 0, 'Regular (50-69)': 0, 'Crítico (<50)': 0 }; 
    const kpiData = currentData?.employee_performance_kpis || [];
    kpiData.forEach(emp => { 
        const sic = emp.SIC || 0; 
        if (sic >= 85) sicRanges['Excelente (>=85)']++; 
        else if (sic >= 70) sicRanges['Bueno (70-84)']++;
        else if (sic >= 50) sicRanges['Regular (50-69)']++;
        else sicRanges['Crítico (<50)']++; 
    }); 

    if(charts.sicDistributionChart) {
        charts.sicDistributionChart.data = { 
            labels: Object.keys(sicRanges), 
            datasets: [{ 
                data: Object.values(sicRanges), 
                backgroundColor: [color('--success-color'), color('--info-color'), color('--warning-color'), color('--danger-color')] 
            }] 
        }; 
    }

    // --- Gráfica 3: Eventos ---
    if(charts.periodEventsChart) {
        charts.periodEventsChart.data = { 
            labels: ['Asistencias', 'Permisos', 'Faltas', 'F. Justificadas'], 
            datasets: [{ 
                data: [summary.total_attendances || 0, summary.total_permissions || 0, summary.total_absences || 0, summary.total_justified_absences || 0], 
                backgroundColor: [color('--success-color'), color('--info-color'), color('--danger-color'), color('--warning-color')] 
            }] 
        }; 
    }

    // --- Gráfica 4: Top Eficiencia (Colores Dinámicos) ---
    const topEmployees = [...kpiData].sort((a, b) => (b['Eficiencia Horas (%)'] || 0) - (a['Eficiencia Horas (%)'] || 0)).slice(0, 10); 
    const efficiencyColors = topEmployees.map(emp => {
        const eficiencia = emp['Eficiencia Horas (%)'] || 0;
        if (eficiencia >= 85) return color('--success-color');
        if (eficiencia >= 50) return color('--warning-color');
        return color('--danger-color');
    });

    if(charts.topEfficiencyChart) {
        charts.topEfficiencyChart.data = { 
            labels: topEmployees.map(b => b.Nombre || 'N/A'), 
            datasets: [{ 
                data: topEmployees.map(b => b['Eficiencia Horas (%)'] || 0), 
                backgroundColor: efficiencyColors
            }] 
        }; 
    }

    // --- Gráfica 5: Radar (Opcional si solo es 1 sucursal) ---
    const radarLabels = ['Eficiencia', 'Puntualidad', 'SIC', 'Productividad']; 
    if(charts.branchComparisonChart) {
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
    }
    
    Object.values(charts).forEach(chart => chart.update()); 
}

// --- EXPORTAR EXCEL ---
async function exportToExcelWithStyles() {
    if (!currentData) {
        alert('No hay datos cargados para exportar.');
        return;
    }

    const btn = document.getElementById('exportExcelBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Preparando...';
    btn.disabled = true;

    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const filename = `Dashboard_31PTE_${startDate}_a_${endDate}.xlsx`; 

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
            } catch(e) { errorMsg = await response.text(); }
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
            if (document.body.contains(a)) document.body.removeChild(a);
        }, 100); 

    } catch (error) {
        console.error('Error Excel:', error);
        alert('Error al generar el archivo: ' + error.message);
    } finally {
        btn.innerHTML = originalText;
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