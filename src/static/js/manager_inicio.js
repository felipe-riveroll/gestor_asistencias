const employeeData = [{"employee": "1", "name": "Beatriz Pérez Reyes", "workedHours": "161:23:47", "expectedHours": "180:00:00", "permitHours": "18:00:00", "netHours": "162:00:00", "delays": 0, "absences": 1, "justifiedAbsences": 2, "totalAbsences": 1, "difference": "-00:36:13", "workedDecimal": 161.39638888888888, "expectedDecimal": 180.0, "expectedDecimalAdjusted": 162.0, "permitDecimal": 18.0}, {"employee": "10", "name": "Jose Juan Guillermo Avila Chavez", "workedHours": "102:39:45", "expectedHours": "108:00:00", "permitHours": "00:00:00", "netHours": "108:00:00", "delays": 0, "absences": 2, "justifiedAbsences": 0, "totalAbsences": 2, "difference": "-05:20:15", "workedDecimal": 102.66250000000001, "expectedDecimal": 108.0, "expectedDecimalAdjusted": 108.0, "permitDecimal": 0.0}, {"employee": "12", "name": "Esmeralda Hernández Lara", "workedHours": "147:31:52", "expectedHours": "160:00:00", "permitHours": "00:00:00", "netHours": "160:00:00", "delays": 0, "absences": 0, "justifiedAbsences": 0, "totalAbsences": 0, "difference": "-12:28:08", "workedDecimal": 147.53111111111113, "expectedDecimal": 160.0, "expectedDecimalAdjusted": 160.0, "permitDecimal": 0.0}, {"employee": "13", "name": "José Omar Villalva Pastrana", "workedHours": "141:38:44", "expectedHours": "160:00:00", "permitHours": "08:00:00", "netHours": "152:00:00", "delays": 3, "absences": 1, "justifiedAbsences": 1, "totalAbsences": 1, "difference": "-10:21:16", "workedDecimal": 141.64555555555555, "expectedDecimal": 160.0, "expectedDecimalAdjusted": 152.0, "permitDecimal": 8.0}, {"employee": "14", "name": "Ivanna Reyes Santamaria", "workedHours": "122:33:00", "expectedHours": "160:00:00", "permitHours": "24:00:00", "netHours": "136:00:00", "delays": 0, "absences": 1, "justifiedAbsences": 3, "totalAbsences": 1, "difference": "-13:27:00", "workedDecimal": 122.55, "expectedDecimal": 160.0, "expectedDecimalAdjusted": 136.0, "permitDecimal": 24.0}, {"employee": "16", "name": "Odalys Castillo Santamaría", "workedHours": "138:32:51", "expectedHours": "160:00:00", "permitHours": "08:00:00", "netHours": "152:00:00", "delays": 8, "absences": 0, "justifiedAbsences": 1, "totalAbsences": 0, "difference": "-13:27:09", "workedDecimal": 138.54749999999999, "expectedDecimal": 160.0, "expectedDecimalAdjusted": 152.0, "permitDecimal": 8.0}, {"employee": "17", "name": "Rodrigo Cabrera Márquez", "workedHours": "150:56:35", "expectedHours": "160:00:00", "permitHours": "00:00:00", "netHours": "160:00:00", "delays": 0, "absences": 1, "justifiedAbsences": 0, "totalAbsences": 1, "difference": "-09:03:25", "workedDecimal": 150.94305555555556, "expectedDecimal": 160.0, "expectedDecimalAdjusted": 160.0, "permitDecimal": 0.0}, {"employee": "2", "name": "Rocío Eufracia García Zamudio", "workedHours": "46:24:14", "expectedHours": "84:00:00", "permitHours": "42:00:00", "netHours": "42:00:00", "delays": 0, "absences": 0, "justifiedAbsences": 6, "totalAbsences": 0, "difference": "+04:24:14", "workedDecimal": 46.403888888888886, "expectedDecimal": 84.0, "expectedDecimalAdjusted": 42.0, "permitDecimal": 42.0}, {"employee": "25", "name": "Karla Ivette Chimal Moreno", "workedHours": "146:19:09", "expectedHours": "160:00:00", "permitHours": "08:00:00", "netHours": "152:00:00", "delays": 0, "absences": 0, "justifiedAbsences": 1, "totalAbsences": 0, "difference": "-05:40:51", "workedDecimal": 146.31916666666666, "expectedDecimal": 160.0, "expectedDecimalAdjusted": 152.0, "permitDecimal": 8.0}, {"employee": "26", "name": "Tanya Maribel Morales Hernandez", "workedHours": "153:32:06", "expectedHours": "160:00:00", "permitHours": "00:00:00", "netHours": "160:00:00", "delays": 1, "absences": 0, "justifiedAbsences": 0, "totalAbsences": 0, "difference": "-06:27:54", "workedDecimal": 153.535, "expectedDecimal": 160.0, "expectedDecimalAdjusted": 160.0, "permitDecimal": 0.0}, {"employee": "27", "name": "Erick Tadeo Ortega Melendez", "workedHours": "152:08:51", "expectedHours": "160:00:00", "permitHours": "08:00:00", "netHours": "152:00:00", "delays": 2, "absences": 1, "justifiedAbsences": 0, "totalAbsences": 1, "difference": "+00:08:51", "workedDecimal": 152.14749999999998, "expectedDecimal": 160.0, "expectedDecimalAdjusted": 152.0, "permitDecimal": 8.0}, {"employee": "28", "name": "Daniela Zarate Castillo", "workedHours": "134:47:24", "expectedHours": "160:00:00", "permitHours": "16:00:00", "netHours": "144:00:00", "delays": 6, "absences": 2, "justifiedAbsences": 1, "totalAbsences": 2, "difference": "-09:12:36", "workedDecimal": 134.79, "expectedDecimal": 160.0, "expectedDecimalAdjusted": 144.0, "permitDecimal": 16.0}, {"employee": "4", "name": "Antonio Rojas", "workedHours": "14:20:19", "expectedHours": "00:00:00", "permitHours": "00:00:00", "netHours": "00:00:00", "delays": 0, "absences": 0, "justifiedAbsences": 0, "totalAbsences": 0, "difference": "+14:20:19", "workedDecimal": 14.338611111111112, "expectedDecimal": 0.0, "expectedDecimalAdjusted": 0.0, "permitDecimal": 0.0}, {"employee": "46", "name": "Mónica Graciela Jiménez López", "workedHours": "121:33:37", "expectedHours": "152:00:00", "permitHours": "00:00:00", "netHours": "152:00:00", "delays": 4, "absences": 3, "justifiedAbsences": 0, "totalAbsences": 3, "difference": "-30:26:23", "workedDecimal": 121.56027777777777, "expectedDecimal": 152.0, "expectedDecimalAdjusted": 152.0, "permitDecimal": 0.0}, {"employee": "47", "name": "Maria Brenda Bautista Zavala", "workedHours": "108:51:01", "expectedHours": "124:00:00", "permitHours": "23:30:00", "netHours": "100:30:00", "delays": 1, "absences": 0, "justifiedAbsences": 5, "totalAbsences": 0, "difference": "+08:21:01", "workedDecimal": 108.85027777777778, "expectedDecimal": 124.0, "expectedDecimalAdjusted": 100.5, "permitDecimal": 23.5}, {"employee": "5", "name": "Marlene Durán Zamudio", "workedHours": "174:56:36", "expectedHours": "180:00:00", "permitHours": "00:00:00", "netHours": "180:00:00", "delays": 0, "absences": 0, "justifiedAbsences": 0, "totalAbsences": 0, "difference": "-05:03:24", "workedDecimal": 174.94333333333333, "expectedDecimal": 180.0, "expectedDecimalAdjusted": 180.0, "permitDecimal": 0.0}, {"employee": "6", "name": "Rebeca Miranda Vergara", "workedHours": "161:44:14", "expectedHours": "180:00:00", "permitHours": "09:00:00", "netHours": "171:00:00", "delays": 15, "absences": 0, "justifiedAbsences": 1, "totalAbsences": 0, "difference": "-09:15:46", "workedDecimal": 161.73722222222221, "expectedDecimal": 180.0, "expectedDecimalAdjusted": 171.0, "permitDecimal": 9.0}, {"employee": "7", "name": "Ana Paola Machorro Buenrostro", "workedHours": "137:22:46", "expectedHours": "160:00:00", "permitHours": "00:00:00", "netHours": "160:00:00", "delays": 0, "absences": 1, "justifiedAbsences": 0, "totalAbsences": 1, "difference": "-22:37:14", "workedDecimal": 137.37944444444446, "expectedDecimal": 160.0, "expectedDecimalAdjusted": 160.0, "permitDecimal": 0.0}, {"employee": "76", "name": "Maximiliano Cuapa Ruiz", "workedHours": "162:57:33", "expectedHours": "160:00:00", "permitHours": "08:00:00", "netHours": "152:00:00", "delays": 0, "absences": 0, "justifiedAbsences": 0, "totalAbsences": 0, "difference": "+10:57:33", "workedDecimal": 162.95916666666665, "expectedDecimal": 160.0, "expectedDecimalAdjusted": 152.0, "permitDecimal": 8.0}, {"employee": "78", "name": "Lizbeth Torres Vazquez", "workedHours": "171:31:49", "expectedHours": "180:00:00", "permitHours": "00:00:00", "netHours": "180:00:00", "delays": 0, "absences": 0, "justifiedAbsences": 0, "totalAbsences": 0, "difference": "-08:28:11", "workedDecimal": 171.5302777777778, "expectedDecimal": 180.0, "expectedDecimalAdjusted": 180.0, "permitDecimal": 0.0}, {"employee": "79", "name": "Juan Jesús Mendoza Muñoz", "workedHours": "176:28:01", "expectedHours": "180:00:00", "permitHours": "00:00:00", "netHours": "180:00:00", "delays": 0, "absences": 1, "justifiedAbsences": 0, "totalAbsences": 1, "difference": "-03:31:59", "workedDecimal": 176.46694444444444, "expectedDecimal": 180.0, "expectedDecimalAdjusted": 180.0, "permitDecimal": 0.0}, {"employee": "8", "name": "Quetzalli López Becerra", "workedHours": "134:43:19", "expectedHours": "160:00:00", "permitHours": "16:00:00", "netHours": "144:00:00", "delays": 0, "absences": 0, "justifiedAbsences": 2, "totalAbsences": 0, "difference": "-09:16:41", "workedDecimal": 134.72194444444446, "expectedDecimal": 160.0, "expectedDecimalAdjusted": 144.0, "permitDecimal": 16.0}, {"employee": "82", "name": "Antonio Alejandro Barbosa Carrillo", "workedHours": "145:10:43", "expectedHours": "160:00:00", "permitHours": "08:00:00", "netHours": "152:00:00", "delays": 7, "absences": 1, "justifiedAbsences": 0, "totalAbsences": 1, "difference": "-06:49:17", "workedDecimal": 145.1786111111111, "expectedDecimal": 160.0, "expectedDecimalAdjusted": 152.0, "permitDecimal": 8.0}, {"employee": "84", "name": "Stephany Morales Hernández", "workedHours": "154:08:47", "expectedHours": "160:00:00", "permitHours": "00:00:00", "netHours": "160:00:00", "delays": 0, "absences": 0, "justifiedAbsences": 0, "totalAbsences": 0, "difference": "-05:51:13", "workedDecimal": 154.14638888888888, "expectedDecimal": 160.0, "expectedDecimalAdjusted": 160.0, "permitDecimal": 0.0}, {"employee": "85", "name": "Brenda Coyotl Tlaxcalteca", "workedHours": "152:29:54", "expectedHours": "160:00:00", "permitHours": "00:00:00", "netHours": "160:00:00", "delays": 0, "absences": 1, "justifiedAbsences": 0, "totalAbsences": 1, "difference": "-07:30:06", "workedDecimal": 152.4983333333333, "expectedDecimal": 160.0, "expectedDecimalAdjusted": 160.0, "permitDecimal": 0.0}, {"employee": "86", "name": "Lorenzo Rojas García", "workedHours": "51:57:02", "expectedHours": "120:00:00", "permitHours": "06:00:00", "netHours": "114:00:00", "delays": 0, "absences": 11, "justifiedAbsences": 1, "totalAbsences": 11, "difference": "-62:02:58", "workedDecimal": 51.95055555555556, "expectedDecimal": 120.0, "expectedDecimalAdjusted": 114.0, "permitDecimal": 6.0}];
        const dailyData = [{"date": "01 Jul", "day": "Martes", "attendance": 21, "absences": 2, "permits": 0, "total": 23}, {"date": "02 Jul", "day": "Miércoles", "attendance": 24, "absences": 1, "permits": 0, "total": 25}, {"date": "03 Jul", "day": "Jueves", "attendance": 23, "absences": 2, "permits": 0, "total": 25}, {"date": "04 Jul", "day": "Viernes", "attendance": 22, "absences": 1, "permits": 2, "total": 25}, {"date": "07 Jul", "day": "Lunes", "attendance": 20, "absences": 2, "permits": 1, "total": 23}, {"date": "08 Jul", "day": "Martes", "attendance": 21, "absences": 1, "permits": 1, "total": 23}, {"date": "09 Jul", "day": "Miércoles", "attendance": 21, "absences": 3, "permits": 1, "total": 25}, {"date": "10 Jul", "day": "Jueves", "attendance": 21, "absences": 2, "permits": 2, "total": 25}, {"date": "11 Jul", "day": "Viernes", "attendance": 21, "absences": 2, "permits": 2, "total": 25}, {"date": "14 Jul", "day": "Lunes", "attendance": 20, "absences": 2, "permits": 1, "total": 23}, {"date": "15 Jul", "day": "Martes", "attendance": 20, "absences": 2, "permits": 1, "total": 23}, {"date": "16 Jul", "day": "Miércoles", "attendance": 23, "absences": 1, "permits": 1, "total": 25}, {"date": "17 Jul", "day": "Jueves", "attendance": 22, "absences": 2, "permits": 1, "total": 25}, {"date": "18 Jul", "day": "Viernes", "attendance": 21, "absences": 0, "permits": 4, "total": 25}, {"date": "21 Jul", "day": "Lunes", "attendance": 21, "absences": 1, "permits": 1, "total": 23}, {"date": "22 Jul", "day": "Martes", "attendance": 22, "absences": 0, "permits": 1, "total": 23}, {"date": "23 Jul", "day": "Miércoles", "attendance": 24, "absences": 0, "permits": 1, "total": 25}, {"date": "24 Jul", "day": "Jueves", "attendance": 24, "absences": 0, "permits": 1, "total": 25}, {"date": "25 Jul", "day": "Viernes", "attendance": 22, "absences": 1, "permits": 2, "total": 25}, {"date": "28 Jul", "day": "Lunes", "attendance": 20, "absences": 2, "permits": 1, "total": 23}];
        const tooltip = d3.select(".tooltip");

// --- UTILS ---
        function hhmmssToDecimal(hhmmss) {
            if (!hhmmss || typeof hhmmss !== 'string') return 0;
            const [h, m, s] = hhmmss.split(':').map(Number);
            return (h || 0) + (m || 0) / 60 + (s || 0) / 3600;
        }
        function safeDiv(numerator, denominator) {
            return denominator > 0 ? numerator / denominator : 0;
        }
        function truncateName(name, max = 20) {
            return name.length > max ? name.slice(0, max) + "…" : name;
        }

// --- PESTAÑAS ---
        function openTab(evt, tabName) {
            document.querySelectorAll('.tab-content').forEach(tc => tc.style.display = 'none');
            document.querySelectorAll('.tab-button').forEach(tb => tb.classList.remove('active'));
            document.getElementById(tabName).style.display = 'block';
            evt.currentTarget.classList.add('active');
        }

// --- CÁLCULO DE KPIs ---
        function calculateAndDisplayKPIs() {
            if (!employeeData || employeeData.length === 0) return;

// Desviación Media Horaria
            const employeesWithPlannedHours = employeeData.filter(e => e.expectedDecimalAdjusted > 0);
            let avgDeviation = 0;
            if (employeesWithPlannedHours.length > 0) {
                const totalDeviation = employeesWithPlannedHours.reduce((sum, e) => {
                    return sum + Math.abs(e.workedDecimal - e.expectedDecimalAdjusted);
                }, 0);
                avgDeviation = safeDiv(totalDeviation, employeesWithPlannedHours.length);
            }
            document.getElementById('avgDeviationHours').textContent = `±${avgDeviation.toFixed(1)} h`;
        }

// --- GRÁFICAS ---
        function createDailyTrendChart() {
            const container = d3.select("#dailyTrendChart");
            if (dailyData.length === 0) { container.text("No hay datos de tendencia diaria."); return; }
            container.html("");
            const margin = { top: 20, right: 100, bottom: 50, left: 40 };
            const width = container.node().getBoundingClientRect().width - margin.left - margin.right;
            const height = 300 - margin.top - margin.bottom;
            const svg = container.append("svg").attr("viewBox", `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom}`)
                .append("g").attr("transform", `translate(${margin.left},${margin.top})`);

            const series = [
                { key: "attendance", label: "Asistencias", color: "#28a745" },
                { key: "absences", label: "Faltas", color: "#dc3545" },
                { key: "permits", label: "Permisos", color: "#ffc107" }
            ];
            const x = d3.scaleBand().domain(dailyData.map(d => d.date)).range([0, width]).padding(0.1);
            const y = d3.scaleLinear().domain([0, d3.max(dailyData, d => d.total) || 1]).nice().range([height, 0]);

            svg.append("g").attr("transform", `translate(0,${height})`).call(d3.axisBottom(x)).selectAll("text").attr("transform", "rotate(-45)").style("text-anchor", "end");
            svg.append("g").call(d3.axisLeft(y));
            svg.append("g").attr("class", "grid").call(d3.axisLeft(y).tickSize(-width).tickFormat("")).selectAll("line").attr("stroke", "#f1f3f4");

            const lineGen = key => d3.line().x(d => x(d.date) + x.bandwidth() / 2).y(d => y(d[key])).curve(d3.curveMonotoneX);

            series.forEach(s => {
                svg.append("path").datum(dailyData).attr("fill", "none").attr("stroke", s.color).attr("stroke-width", 2.5).attr("d", lineGen(s.key));
                svg.selectAll(`.dot-${s.key}`).data(dailyData).enter().append("circle")
                    .attr("cx", d => x(d.date) + x.bandwidth() / 2).attr("cy", d => y(d[s.key])).attr("r", 4).attr("fill", s.color)
                    .on("mouseover", (event, d) => tooltip.style("opacity", 1).html(`<strong>${d.date}</strong><br>${s.label}: ${d[s.key]}`))
                    .on("mousemove", e => tooltip.style("left", (e.pageX + 10) + "px").style("top", (e.pageY - 10) + "px"))
                    .on("mouseout", () => tooltip.style("opacity", 0));
            });
        }

        function createEfficiencyChart() {
            const container = d3.select("#efficiencyChart");
            container.html("");

            const data = employeeData
                .map(d => ({
                    name: truncateName(d.name),
                    fullName: d.name,
                    efficiency: safeDiv(d.workedDecimal, d.expectedDecimalAdjusted) * 100,
                    worked: d.workedDecimal,
                    planned: d.expectedDecimalAdjusted
                }))
                .filter(d => d.planned > 0)
                .sort((a, b) => b.efficiency - a.efficiency)
                .slice(0, 15);

            if (data.length === 0) { container.text("No hay datos de eficiencia para mostrar (sin horas planificadas)."); return; }

            const margin = { top: 20, right: 30, bottom: 40, left: 150 };
            const width = container.node().getBoundingClientRect().width - margin.left - margin.right;
            const height = data.length * 28;
            const svg = container.append("svg").attr("viewBox", `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom}`)
                .append("g").attr("transform", `translate(${margin.left},${margin.top})`);

            const x = d3.scaleLinear().domain([0, Math.max(100, d3.max(data, d => d.efficiency) || 0)]).nice().range([0, width]);
            const y = d3.scaleBand().domain(data.map(d => d.name)).range([0, height]).padding(0.1);

            svg.append("g").call(d3.axisLeft(y).tickSize(0)).select(".domain").remove();
            svg.append("g").attr("transform", `translate(0,${height})`).call(d3.axisBottom(x).ticks(5).tickFormat(d => d + "%"));

            svg.append("line").attr("x1", x(100)).attr("x2", x(100)).attr("y1", 0).attr("y2", height).attr("stroke", "#dc3545").attr("stroke-dasharray", "4,4");

            svg.selectAll(".bar").data(data).enter().append("rect")
                .attr("y", d => y(d.name)).attr("width", d => x(d.efficiency)).attr("height", y.bandwidth())
                .attr("fill", d => d.efficiency >= 98 ? "#28a745" : d.efficiency >= 85 ? "#ffc107" : "#dc3545")
                .on("mouseover", (event, d) => tooltip.style("opacity", 1).html(`<strong>${d.fullName}</strong><br>Eficiencia: ${d.efficiency.toFixed(1)}%<br>Trabajadas: ${d.worked.toFixed(1)}h<br>Planificadas: ${d.planned.toFixed(1)}h`))
                .on("mousemove", e => tooltip.style("left", (e.pageX + 10) + "px").style("top", (e.pageY - 10) + "px"))
                .on("mouseout", () => tooltip.style("opacity", 0));
        }

        function createAbsenceImpactChart() {
            const container = d3.select("#absenceImpactChart");
            container.html("");

            const unjustified = d3.sum(employeeData, d => d.absences);
            const justified = d3.sum(employeeData, d => d.justifiedAbsences);
            const delays = d3.sum(employeeData, d => d.delays);

            const data = [
                { type: "Faltas Injustificadas", count: unjustified, color: "#dc3545" },
                { type: "Faltas Justificadas", count: justified, color: "#ffc107" },
                { type: "Retardos", count: delays, color: "#17a2b8" }
            ].filter(d => d.count > 0);

            if (data.length === 0) { container.text("¡Sin ausencias ni retardos en el período!"); return; }

            const margin = { top: 20, right: 20, bottom: 30, left: 40 };
            const width = container.node().getBoundingClientRect().width - margin.left - margin.right;
            const height = 300 - margin.top - margin.bottom;
            const svg = container.append("svg").attr("viewBox", `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom}`)
                .append("g").attr("transform", `translate(${margin.left},${margin.top})`);

            const x = d3.scaleBand().domain(data.map(d => d.type)).range([0, width]).padding(0.4);
            const y = d3.scaleLinear().domain([0, d3.max(data, d => d.count) || 1]).nice().range([height, 0]);

            svg.append("g").attr("transform", `translate(0,${height})`).call(d3.axisBottom(x));
            svg.append("g").call(d3.axisLeft(y));

            svg.selectAll(".bar").data(data).enter().append("rect")
                .attr("x", d => x(d.type)).attr("y", d => y(d.count))
                .attr("width", x.bandwidth()).attr("height", d => height - y(d.count))
                .attr("fill", d => d.color)
                .on("mouseover", (event, d) => tooltip.style("opacity", 1).html(`<strong>${d.type}</strong><br>Total: ${d.count}`))
                .on("mousemove", e => tooltip.style("left", (e.pageX + 10) + "px").style("top", (e.pageY - 10) + "px"))
                .on("mouseout", () => tooltip.style("opacity", 0));
        }

// --- TABLA ---
        function renderTable(data) {
            const tableBody = document.getElementById('tableBody');
            tableBody.innerHTML = data.map(emp => `
                <tr>
                    <td>${emp.employee}</td>
                    <td>${emp.name}</td>
                    <td>${emp.workedHours}</td>
                    <td>${emp.netHours}</td>
                    <td class="${emp.difference.startsWith('+') ? 'positive' : 'negative'}">${emp.difference}</td>
                    <td>${emp.delays}</td>
                    <td>${emp.totalAbsences}</td>
                </tr>
            `).join('');
        }

        function filterTable() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const filteredData = employeeData.filter(e => 
                e.name.toLowerCase().includes(searchTerm) || 
                e.employee.toLowerCase().includes(searchTerm)
            );
            renderTable(filteredData);
        }

// --- INICIALIZACIÓN ---
        document.addEventListener('DOMContentLoaded', () => {
            calculateAndDisplayKPIs();
            createDailyTrendChart();
            createEfficiencyChart();
            createAbsenceImpactChart();
            renderTable(employeeData);

            window.addEventListener('resize', () => {
                createDailyTrendChart();
                createEfficiencyChart();
                createAbsenceImpactChart();
            });
        });