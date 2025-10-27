# Imports de Django
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.http import JsonResponse, HttpResponse # <--- HttpResponse AÑADIDO

# Imports de librerías externas
import json
from io import BytesIO
import openpyxl
from openpyxl.styles import PatternFill, Border, Side

# Imports de tus propios archivos de la aplicación
# Solo importamos helpers y la clase de cálculo desde services
from .services import autenticar_usuario, crear_empleado_service, crear_horario_service
from .models import Sucursal, Horario, Empleado
# MODIFICADO: Las funciones orquestadoras se importan desde main
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
        # Imprimir todo el POST para debug
        print("===== [DEBUG] request.POST =====")
        for key, value in request.POST.lists():
            print(f"{key}: {value}")
        print("================================")

        try:
            # Pasamos directamente el POST al service
            crear_empleado_service(request.POST)
            messages.success(request, "Empleado creado correctamente.")
        except Exception as e:
            print("[ERROR en crear_empleado]:", str(e))
            messages.error(request, f"Error al crear empleado: {e}")

        # Redirige después del POST para evitar resubmit
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

@login_required
@require_http_methods(["POST"])
def exportar_excel_con_colores(request):
    """
    API para generar y exportar un archivo Excel con múltiples hojas y filas coloreadas.
    """
    try:
        data = json.loads(request.body)
        nombre_archivo = data.get('nombre_archivo', 'reporte')
        sheets_data = data.get('sheets', {})

        if not sheets_data:
            return JsonResponse({'error': 'No hay datos de hojas para exportar'}, status=400)

        wb = openpyxl.Workbook()
        wb.remove(wb.active) # Eliminamos la hoja por defecto

        # Define el estilo de borde
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        ) 

        color_map = {
            # --- Colores de la leyenda (Corregidos)
            'fila-ok': '92D050', # "Checado Normal" -> Verde Brillante
            'fila-retardo-normal': 'FFFF00', # "Retardo Normal" -> Amarillo Brillante
            'fila-falta': 'FF0000', # "Falta" -> Rojo Brillante
            'fila-descanso': 'B2A1C7', # "Fines de Semana" -> Morado Pálido
            'fila-permiso': 'E2EFDA', # "Permiso" -> Verde Pálido

            # --- Colores que no están en la leyenda (se quedan como estaban) 
            'fila-retardo-mayor': 'FFD966', # Amarillo
            'fila-salida-anticipada': 'F8CBAD', # Naranja pálido
            'fila-retardo-cumplido': 'E6D4ED', # Morado pálido
        }

        # Iteramos sobre cada hoja de datos que nos llega desde el frontend
        for sheet_name, sheet_content in sheets_data.items():
            ws = wb.create_sheet(title=sheet_name.capitalize())
            
            datos = sheet_content.get('datos', [])
            colores_clases = sheet_content.get('colores', [])

            if not datos: continue

            # --- 1. ENCABEZADOS ---
            ws.append(datos[0])
            # Aplica borde a los encabezados
            header_fill = PatternFill(start_color="8DB4E3", end_color="8DB4E3", fill_type="solid") # Un azul claro, puedes cambiar "CCE0FF"
            for cell in ws[1]: # ws[1] es la primera fila (encabezados)
                cell.border = thin_border
                cell.fill = header_fill # <--- ¡Aquí se aplica el color!

            # --- 2. FILAS DE DATOS (AQUÍ ESTÁ LA CORRECCIÓN) ---
            # Este es el ÚNICO bucle para los datos
            for i, row_data in enumerate(datos[1:]):
                
                # a) Agrega la fila de datos
                ws.append(row_data)
                
                # b) Obtén las celdas de la fila que acabamos de agregar (ws.max_row)
                new_row_cells = ws[ws.max_row]

                # c) Aplica color a esa fila (si es necesario)
                if i < len(colores_clases) and colores_clases[i] in color_map:
                    fill = PatternFill(start_color=color_map[colores_clases[i]], end_color=color_map[colores_clases[i]], fill_type="solid")
                    for cell in new_row_cells:
                        cell.fill = fill
                
                # d) Aplica borde a TODAS las celdas de esa fila (siempre)
                for cell in new_row_cells: 
                    cell.border = thin_border
            
            # --- 3. AUTOAJUSTE DE COLUMNAS (Tu código original está perfecto) ---
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                ws.column_dimensions[column].width = (max_length + 2)

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}.xlsx"'
        return response
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

#Gráficas
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