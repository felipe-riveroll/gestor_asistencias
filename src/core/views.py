# Imports de Django
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.http import JsonResponse, HttpResponse

# Imports de librerías externas
import json
from io import BytesIO
import openpyxl
# ✅ CORRECCIÓN: Se añaden las importaciones que faltaban para el Excel
from openpyxl.styles import PatternFill, Border, Side, Alignment, Font
from openpyxl.utils import get_column_letter

# Imports de tus propios archivos de la aplicación
from .services import autenticar_usuario, crear_empleado_service, crear_horario_service
from .models import Sucursal, Horario, Empleado
from .main import generar_reporte_completo, generar_reporte_detalle_completo, generar_datos_dashboard_general
 
def inicio(request):
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login') 

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = autenticar_usuario(request, email, password)

        if user is not None:
            login(request, user)

             # Redirección según grupo
            if user.groups.filter(name="Admin").exists():
                return redirect("admin_page")
            elif user.groups.filter(name="Manager").exists():
                return redirect("manager-page")
            else:
                messages.error(request, "No tienes permisos para ingresar.")
        else:
            messages.error(request, "Correo o contraseña incorrectos.")
        return redirect("login")
    
    return render(request, "login.html")

@login_required
def admin_page(request):
    return render(request, "admin_inicio.html")

@login_required
def manager_page(request):
    return render(request, "manager_inicio.html")


@login_required
def gestion_empleados(request):
    empleados = Empleado.objects.all()
    sucursales = Sucursal.objects.all()
    horarios = Horario.objects.all()
    return render(request, "gestion_empleados.html", {
        "empleados": empleados,
        "sucursales": sucursales,
        "horarios": horarios,
    })

@login_required
def crear_empleado(request):
    if request.method == "POST":
        print("===== [DEBUG] request.POST =====")
        for key, value in request.POST.lists():
            print(f"{key}: {value}")
        print("================================")

        try:
            crear_empleado_service(request.POST)
            messages.success(request, "Empleado creado correctamente.")
        except Exception as e:
            print("[ERROR en crear_empleado]:", str(e))
            messages.error(request, f"Error al crear empleado: {e}")

        return redirect('admin-gestion-empleados')

    return render(request, "gestion_empleados.html")

@login_required
def eliminar_empleado(request, empleado_id):
    empleado = get_object_or_404(Empleado, empleado_id=empleado_id)
    empleado.delete()
    return redirect("admin-gestion-empleados")

@login_required
def crear_horario(request):
    if request.method == "POST":
        crear_horario_service(request.POST)
        messages.success(request, "Horario creado correctamente")
        return redirect("admin-gestion-empleados")
    return render(request, "admin-gestion-empleados")

@login_required
def gestion_usuarios(request):
    return render(request, "gestion_usuarios.html")

#Reporte de Horas y Lista de Asistencias
@login_required
def reporte_horas(request):
    sucursales = Sucursal.objects.all()
    return render(request, "reporte_horas.html", {"sucursales": sucursales})

@login_required
def lista_asistencias(request):
    sucursales = Sucursal.objects.all()
    return render(request, "lista_asistencias.html", {"sucursales": sucursales})

# --- Vistas de API y Health Check ---

@require_http_methods(["GET"])
def health_check(request):
    """Endpoint para verificar el estado del servicio."""
    return JsonResponse({'status': 'healthy'}, status=200)

@login_required
@require_http_methods(["GET"])
def api_reporte_horas(request):
    """API para el reporte de horas (resumen). Delega toda la lógica a main.py."""
    try:
        start_date = request.GET.get("startDate")
        end_date = request.GET.get("endDate") 
        sucursal = request.GET.get("sucursal", "Todas")
        if not start_date or not end_date:
            return JsonResponse({"error": "Debe proporcionar fecha de inicio y fin."}, status=400)
        resultado = generar_reporte_completo(start_date=start_date, end_date=end_date, sucursal=sucursal)
        return JsonResponse(resultado)
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Error interno del servidor: {str(e)}"}, status=500)

@login_required
@require_http_methods(["GET"])
def api_reporte_detalle(request):
    """API para el reporte detallado. Delega toda la lógica a main.py."""
    try:
        start_date = request.GET.get("startDate")
        end_date = request.GET.get("endDate")
        sucursal = request.GET.get("sucursal", "Todas")
        if not start_date or not end_date:
            return JsonResponse({"success": False, "error": "Debe proporcionar fecha de inicio y fin."}, status=400)
        resultado = generar_reporte_detalle_completo(start_date=start_date, end_date=end_date, sucursal=sucursal)
        return JsonResponse(resultado)
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Error interno del servidor: {str(e)}"}, status=500)

# ❌ VISTA 'exportar_excel_con_colores' (que usaba POST) ELIMINADA 
#    Se reemplaza por 'export_dashboard_excel' (que usa GET)

# --- Gráficas y Dashboard ---
@login_required
def grafica_general(request):
    return render(request, "grafica_general.html")

@login_required
@require_http_methods(["GET"])
def api_dashboard_general(request):
    """API para proveer datos al dashboard general, agregados por sucursal."""
    try:
        start_date = request.GET.get("startDate")
        end_date = request.GET.get("endDate")
        if not start_date or not end_date:
            return JsonResponse({"success": False, "error": "Fechas de inicio y fin son requeridas."}, status=400)
        
        resultado = generar_datos_dashboard_general(start_date=start_date, end_date=end_date)
        return JsonResponse(resultado)

    except Exception as e:
        return JsonResponse({"success": False, "error": f"Error interno del servidor: {str(e)}"}, status=500)

# --- EN views.py ---
# =================================================================
# === EXPORTACIÓN DE EXCEL (UNIFICADA Y MEJORADA) ===
# =================================================================

@login_required
@require_http_methods(["POST"]) 
def exportar_excel_con_colores(request):
    """
    VISTA DE RESPALDO: Genera Excel para Reporte de Horas o Asistencias Detalle.
    Recibe los datos de la tabla (y la clase CSS de la fila) desde el frontend.
    """
    try:
        data = json.loads(request.body)
        nombre_archivo = data.get('nombre_archivo', 'reporte')
        sheets_data = data.get('sheets', {})

        if not sheets_data:
            return JsonResponse({'error': 'No hay datos de hojas para exportar'}, status=400)

        wb = openpyxl.Workbook()
        wb.remove(wb.active) # Eliminamos la hoja por defecto

        # --- Definir Estilos (Lógica de colores de filas) ---
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        header_fill = PatternFill(start_color="8DB4E3", end_color="8DB4E3", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        header_align = Alignment(horizontal='center', vertical='center')
        
        # Mapa de colores (basado en tu código original)
        color_map = {
            'fila-ok': '92D050', 'fila-retardo-normal': 'FFFF00', 'fila-falta': 'FF0000', 
            'fila-descanso': 'B2A1C7', 'fila-permiso': 'FFC0CB', 'fila-retardo-mayor': 'FF9900',
            'fila-salida-anticipada': 'E76F51', 'fila-retardo-cumplido': 'E6D4ED', 
            'fila-totales': 'DDEBF7'
        }

        # --- Iterar sobre las hojas ---
        for sheet_name, sheet_content in sheets_data.items():
            ws = wb.create_sheet(title=sheet_name.capitalize())
            
            datos = sheet_content.get('datos', [])
            colores_clases = sheet_content.get('colores', []) 

            if not datos: continue

            # --- 1. Encabezados ---
            ws.append(datos[0])
            for cell in ws[1]:
                cell.border = thin_border
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_align

            # --- 2. Filas de Datos ---
            for i, row_data in enumerate(datos[1:]): 
                ws.append(row_data)
                clase_color = colores_clases[i] if i < len(colores_clases) else None
                fill_color = None
                if clase_color in color_map:
                    fill_color = PatternFill(start_color=color_map[clase_color], end_color=color_map[clase_color], fill_type="solid")

                for cell in ws[ws.max_row]: 
                    cell.border = thin_border
                    if fill_color:
                        cell.fill = fill_color
                    cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # --- 3. Autoajuste de Columnas ---
            for col in ws.columns:
                max_length = 0
                column_letter = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min((max_length + 4), 50) 
                ws.column_dimensions[column_letter].width = adjusted_width

        # --- Guardar y Enviar ---
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}.xlsx"'
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"]) # Mantenemos POST ya que el JS lo envía así
def export_dashboard_excel(request):
    """
    VISTA PRINCIPAL: Genera y descarga el Excel del Dashboard General (3 hojas).
    Recibe el JSON con los datos CALCULADOS desde el frontend.
    ADOPTADA DE TU COMPAÑERA por ser más completa y usar 3 hojas.
    """
    print(f"🔍 [EXPORT] Método recibido: {request.method}")
    print(f"🔍 [EXPORT] Referer: {request.META.get('HTTP_REFERER', 'No referer')}")
    
    if request.method == 'POST':
        try:
            print("✅ [EXPORT] Procesando solicitud POST válida")
            
            # 1. Leer los datos JSON que envió el JavaScript
            data_from_js = json.loads(request.body)
            
            # Extraer los datos para las 3 hojas
            branches_data = data_from_js.get("branches", [])
            employee_summary_data = data_from_js.get("employee_summary_kpis", [])
            employee_kpis_data = data_from_js.get("employee_performance_kpis", [])
            
            print(f"✅ [EXPORT] Datos recibidos para exportación:")
            print(f"    - Sucursales: {len(branches_data)} registros")
            print(f"    - Resumen empleados: {len(employee_summary_data)} registros")
            print(f"    - KPIs empleados: {len(employee_kpis_data)} registros")

            if not branches_data and not employee_summary_data and not employee_kpis_data:
                 return JsonResponse({"error": "No hay datos para exportar."}, status=404)

            # --- Crear Libro y Estilos (Lógica de tu compañera) ---
            wb = openpyxl.Workbook()
            wb.remove(wb.active)
            
            # Colores (RGB Hex sin #, usando los de tu compañera)
            colors = {
                'headerBg': '2F5496', 'headerFont': 'FFFFFF', 'successFill': 'C6EFCE', 'successFont': '006100',
                'warningFill': 'FFEB9C', 'warningFont': '9C6500', 'dangerFill': 'FFC7CE', 'dangerFont': '9C0006',
                'totalFill': 'F0F0F0', 'legendHeaderFill': 'BFBFBF', 'legendFont': '595959'
            }
            
            # Estilos
            header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
            center_align = Alignment(horizontal='center', vertical='center')
            left_align = Alignment(horizontal='left', vertical='center')
            right_align = Alignment(horizontal='right', vertical='center')
            
            header_font = Font(color=colors['headerFont'], bold=True, size=11)
            success_font = Font(color=colors['successFont']); warning_font = Font(color=colors['warningFont'])
            danger_font = Font(color=colors['dangerFont']); total_font = Font(bold=True)
            legend_header_font = Font(bold=True, size=12); legend_text_font = Font(italic=True, size=10, color=colors['legendFont'])
            
            header_fill = PatternFill(start_color=colors['headerBg'], end_color=colors['headerBg'], fill_type="solid")
            success_fill = PatternFill(start_color=colors['successFill'], end_color=colors['successFill'], fill_type="solid")
            warning_fill = PatternFill(start_color=colors['warningFill'], end_color=colors['warningFill'], fill_type="solid")
            danger_fill = PatternFill(start_color=colors['dangerFill'], end_color=colors['dangerFill'], fill_type="solid")
            total_fill = PatternFill(start_color=colors['totalFill'], end_color=colors['totalFill'], fill_type="solid")
            legend_header_fill = PatternFill(start_color=colors['legendHeaderFill'], end_color=colors['legendHeaderFill'], fill_type="solid")

            # Formatos de Número
            number_format_percent_2dec = '0.00%' ; number_format_percent_1dec = '0.0%'
            number_format_decimal_2dec = '0.00'; number_format_integer = '0';
            # number_format_time = '[h]:mm:ss' # No usado para campos de tiempo en este script
            thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))


            # --- Hoja 1: Resumen Sucursal (Logic: tu compañera) ---
            if branches_data:
                print("📊 [EXPORT] Creando hoja: Resumen Sucursal")
                ws1 = wb.create_sheet(title="Resumen Sucursal")
                
                headers1 = ['Sucursal', 'Empleados', 'Eficiencia (%)', 'Puntualidad (%)', 'SIC Promedio', 'Ausencias']
                ws1.append(headers1)
                
                for col_idx, header in enumerate(headers1, 1):
                    cell = ws1.cell(row=1, column=col_idx)
                    cell.fill = header_fill; cell.font = header_font; cell.alignment = header_align; cell.border = thin_border
                    
                num_branches = len(branches_data)
                total_employees = sum(b.get('employees', 0) for b in branches_data)
                total_absences = sum(b.get('absences', 0) for b in branches_data)
                avg_efficiency = sum(b.get('efficiency', 0) for b in branches_data) / num_branches if num_branches > 0 else 0
                avg_punctuality = sum(b.get('punctuality', 0) for b in branches_data) / num_branches if num_branches > 0 else 0
                avg_sic = sum(b.get('avgSIC', 0) for b in branches_data) / num_branches if num_branches > 0 else 0
                
                for row_idx, branch in enumerate(branches_data, 2):
                    ws1.cell(row=row_idx, column=1, value=branch.get('name', 'N/A'))
                    ws1.cell(row=row_idx, column=2, value=branch.get('employees', 0)).number_format = number_format_integer
                    
                    c3 = ws1.cell(row=row_idx, column=3, value=branch.get('efficiency', 0) / 100)
                    c3.number_format = number_format_percent_1dec
                    
                    c4 = ws1.cell(row=row_idx, column=4, value=branch.get('punctuality', 0) / 100)
                    c4.number_format = number_format_percent_1dec
                    
                    c5 = ws1.cell(row=row_idx, column=5, value=branch.get('avgSIC', 0))
                    c5.number_format = number_format_decimal_2dec
                    
                    ws1.cell(row=row_idx, column=6, value=branch.get('absences', 0)).number_format = number_format_integer
                    
                    eff_val = c3.value; pun_val = c4.value; sic_val = c5.value
                    if eff_val is not None:
                        if eff_val >= 0.95: c3.fill = success_fill; c3.font = success_font
                        elif eff_val >= 0.85: c3.fill = warning_fill; c3.font = warning_font
                        else: c3.fill = danger_fill; c3.font = danger_font
                    
                    if pun_val is not None:
                        if pun_val >= 0.95: c4.fill = success_fill; c4.font = success_font
                        elif pun_val >= 0.85: c4.fill = warning_fill; c4.font = warning_font
                        else: c4.fill = danger_fill; c4.font = danger_font
                    
                    if sic_val is not None:
                        if sic_val >= 85: c5.fill = success_fill; c5.font = success_font
                        elif sic_val >= 50: c5.fill = warning_fill; c5.font = warning_font
                        else: c5.fill = danger_fill; c5.font = danger_font
                        
                    for c_idx in range(1, len(headers1) + 1):
                        ws1.cell(row=row_idx, column=c_idx).border = thin_border
                        
                total_row_idx = len(branches_data) + 2
                ws1.cell(row=total_row_idx, column=1, value='PROMEDIO / TOTAL')
                ws1.cell(row=total_row_idx, column=2, value=total_employees).number_format = number_format_integer
                ws1.cell(row=total_row_idx, column=3, value=avg_efficiency / 100).number_format = number_format_percent_1dec
                ws1.cell(row=total_row_idx, column=4, value=avg_punctuality / 100).number_format = number_format_percent_1dec
                ws1.cell(row=total_row_idx, column=5, value=avg_sic).number_format = number_format_decimal_2dec
                ws1.cell(row=total_row_idx, column=6, value=total_absences).number_format = number_format_integer
                
                for col_idx in range(1, len(headers1) + 1):
                    cell = ws1.cell(row=total_row_idx, column=col_idx)
                    cell.fill = total_fill; cell.font = total_font; cell.border = thin_border
                        
                column_widths = [25, 12, 15, 15, 15, 12]
                for i, width in enumerate(column_widths, 1): ws1.column_dimensions[get_column_letter(i)].width = width

            # --- Hoja 2: Resumen Horas por Empleado (Logic: tu compañera) ---
            if employee_summary_data:
                print("📊 [EXPORT] Creando hoja: Resumen Horas Emp.")
                ws2 = wb.create_sheet(title="Resumen Horas Emp.")
                
                headers2 = ['ID', 'Empleado', 'Hrs. Trabajadas', 'Hrs. Planificadas', 'Variación', 'Retardos', 'Ausencias']
                ws2.append(headers2)
                
                for col_idx, header in enumerate(headers2, 1):
                    cell = ws2.cell(row=1, column=col_idx)
                    cell.fill = header_fill; cell.font = header_font; cell.alignment = header_align; cell.border = thin_border
                    
                for row_idx, emp in enumerate(employee_summary_data, 2):
                    ws2.cell(row=row_idx, column=1, value=emp.get('ID', 'N/A'))
                    ws2.cell(row=row_idx, column=2, value=emp.get('Empleado', 'Sin Nombre'))
                    ws2.cell(row=row_idx, column=3, value=emp.get('Hrs. Trabajadas', '0:00:00'))
                    ws2.cell(row=row_idx, column=4, value=emp.get('Hrs. Planificadas', '0:00:00'))
                    ws2.cell(row=row_idx, column=5, value=emp.get('Variación', '0:00:00'))
                    
                    cell_retardos = ws2.cell(row=row_idx, column=6, value=emp.get('Retardos', 0))
                    cell_retardos.number_format = number_format_integer
                    
                    cell_ausencias = ws2.cell(row=row_idx, column=7, value=emp.get('Ausencias', 0))
                    cell_ausencias.number_format = number_format_integer
                    
                    for c in range(1, len(headers2) + 1):
                        ws2.cell(row=row_idx, column=c).border = thin_border
                        
                column_widths2 = [10, 40, 18, 18, 15, 12, 12]
                for i, width in enumerate(column_widths2, 1): ws2.column_dimensions[get_column_letter(i)].width = width


            # --- Hoja 3: KPIs por Empleado (Logic: tu compañera) ---
            if employee_kpis_data:
                print("📊 [EXPORT] Creando hoja: KPIs Empleado")
                ws3 = wb.create_sheet(title="KPIs Empleado")
                headers3 = ['ID', 'Nombre', 'Tasa Ausentismo (%)', 'Índice Puntualidad (%)', 'Eficiencia Horas (%)', 'SIC']
                ws3.append(headers3)
                
                for col_idx, header in enumerate(headers3, 1):
                    cell = ws3.cell(row=1, column=col_idx)
                    cell.fill = header_fill; cell.font = header_font; cell.alignment = header_align; cell.border = thin_border

                # Se insertan filas para título (como hace tu compañera)
                ws3.insert_rows(1); ws3.insert_rows(1)
                title_cell = ws3.cell(row=1, column=1, value="Análisis de KPIs por Empleado")
                subtitle_cell = ws3.cell(row=2, column=1, value="Indicadores de Rendimiento Individual")
                green_fill = PatternFill(start_color="00B050", end_color="00B050", fill_type="solid")
                white_font = Font(color="FFFFFF", bold=True, size=12)
                title_cell.fill = green_fill; title_cell.font = white_font
                subtitle_cell.fill = green_fill; subtitle_cell.font = white_font
                ws3.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers3)); ws3.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(headers3))


                for row_idx, emp in enumerate(employee_kpis_data, 4): # Empieza en Fila 4 por los títulos
                    emp_id = emp.get('ID', 'N/A'); emp_nombre = emp.get('Nombre', 'Sin Nombre')
                    tasa_ausentismo_val = emp.get('Tasa Ausentismo (%)', 0) / 100 if emp.get('Tasa Ausentismo (%)') is not None else None
                    puntualidad_val = emp.get('Índice Puntualidad (%)', 0) / 100 if emp.get('Índice Puntualidad (%)') is not None else None
                    eficiencia_val = emp.get('Eficiencia Horas (%)', 0) / 100 if emp.get('Eficiencia Horas (%)') is not None else None
                    sic_val = emp.get('SIC', 0) if emp.get('SIC') is not None else None

                    ws3.cell(row=row_idx, column=1, value=emp_id); ws3.cell(row=row_idx, column=2, value=emp_nombre)
                    c3 = ws3.cell(row=row_idx, column=3, value=tasa_ausentismo_val); c3.number_format = number_format_percent_2dec
                    c4 = ws3.cell(row=row_idx, column=4, value=puntualidad_val); c4.number_format = number_format_percent_2dec
                    c5 = ws3.cell(row=row_idx, column=5, value=eficiencia_val); c5.number_format = number_format_percent_2dec
                    c6 = ws3.cell(row=row_idx, column=6, value=sic_val); c6.number_format = number_format_decimal_2dec

                    for col_idx in range(1, len(headers3) + 1):
                        cell = ws3.cell(row=row_idx, column=col_idx)
                        cell.border = thin_border
                        cell.alignment = right_align if col_idx > 2 else left_align
                        if col_idx == 1: cell.alignment = center_align

                        value = cell.value

                        # Aplicación de estilos condicionales (lógica copiada de tu JS)
                        if col_idx == 3: # Tasa Ausentismo
                            if value is not None:
                                if value < 0.05: cell.fill = success_fill; cell.font = success_font
                                elif value <= 0.10: cell.fill = warning_fill; cell.font = warning_font
                                else: cell.fill = danger_fill; cell.font = danger_font
                        elif col_idx == 4: # Puntualidad
                            if value is not None:
                                if value >= 0.95: cell.fill = success_fill; cell.font = success_font
                                elif value >= 0.70: cell.fill = warning_fill; cell.font = warning_font
                                else: cell.fill = danger_fill; cell.font = danger_font
                        elif col_idx == 5: # Eficiencia
                            if value is not None:
                                if value > 1.00: cell.fill = success_fill; cell.font = success_font
                                elif value >= 0.85: cell.fill = warning_fill; cell.font = warning_font
                                else: cell.fill = danger_fill; cell.font = danger_font
                        elif col_idx == 6: # SIC (Usa el valor sin dividir por 100)
                            if sic_val is not None:
                                if sic_val >= 85: cell.fill = success_fill; cell.font = success_font
                                elif sic_val >= 50: cell.fill = warning_fill; cell.font = warning_font
                                else: cell.fill = danger_fill; cell.font = danger_font
                
                # Leyenda (Logica tu compañera)
                legend_start_row = len(employee_kpis_data) + 5
                legend = [
                    ["Interpretación de KPIs:"],
                    ["• Tasa Ausentismo: <5% (Excelente), 5-10% (Aceptable), >10% (Alto)"],
                    ["• Índice Puntualidad: >95 (Excelente), 70-95 (Regular), <70 (Crítico)"],
                    ["• Eficiencia Horas: >100% (Excelente), 85-100% (Regular), <85% (Crítico)"], 
                    ["• SIC: >85 (Excelente), 50-85 (Regular), <50 (Crítico)"] 
                ]
                
                for i, text_list in enumerate(legend):
                    cell = ws3.cell(row=legend_start_row + i, column=1, value=text_list[0])
                    last_col_idx = len(headers3)
                    
                    if i == 0:
                        cell.fill = legend_header_fill; cell.font = legend_header_font; cell.alignment = center_align
                        ws3.merge_cells(start_row=legend_start_row + i, start_column=1, end_row=legend_start_row + i, end_column=last_col_idx)
                    else:
                        cell.font = legend_text_font; cell.alignment = left_align
                        ws3.merge_cells(start_row=legend_start_row + i, start_column=1, end_row=legend_start_row + i, end_column=last_col_idx)

                column_widths3 = [10, 40, 20, 22, 22, 10]
                for i, width in enumerate(column_widths3, 1): ws3.column_dimensions[get_column_letter(i)].width = width


            # --- Guardar y Enviar ---
            if not wb.sheetnames:
                return JsonResponse({"error": "No se generaron datos para exportar."}, status=404)
            
            print(f"💾 [EXPORT] Guardando Excel con {len(wb.sheetnames)} hojas")
            buffer = BytesIO()
            wb.save(buffer)
            buffer.seek(0)
            
            response = HttpResponse(
                buffer.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="dashboard_report.xlsx"'
            print("✅ [EXPORT] Response preparada - enviando archivo Excel")
            return response

        except json.JSONDecodeError as e:
            print(f"🔴 [EXPORT] Error decodificando JSON: {e}")
            return JsonResponse({'error': f"Error en formato JSON: {e}"}, status=400)
        except Exception as e:
            import traceback
            print(f"🔴 [EXPORT] Error inesperado: {e}")
            traceback.print_exc()
            return JsonResponse({'error': f"Error interno: {e}"}, status=500)
    
    # Esto maneja el caso de que alguien intente GET (para diagnóstico)
    print("⚠️ [EXPORT] Se recibió un método no POST. Mostrando diagnóstico.")
    return JsonResponse({
        'error': 'Método GET no permitido para exportación',
        'expected_method': 'POST',
        'debug_info': {
            'user_agent': request.META.get('HTTP_USER_AGENT'),
            'referer': request.META.get('HTTP_REFERER'),
            'path': request.path,
            'query_params': dict(request.GET),
            'timestamp': str(timezone.now()) 
        }
    }, status=405)