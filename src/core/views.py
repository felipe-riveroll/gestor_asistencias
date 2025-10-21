# Imports de Django
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.http import JsonResponse

# Imports de librerías externas
import pandas as pd
import time

# Imports de tus propios archivos de la aplicación
from .services import autenticar_usuario, crear_empleado_service, crear_horario_service, generar_reporte_asistencia
from .api_client import APIClient, procesar_permisos_empleados
from .models import Sucursal, Horario, Empleado, AsignacionHorario, DiaSemana
from .main import generar_reporte_completo
 

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
    sucursales = Sucursal.objects.all()
    return render(request, "reporte_horas.html", {"sucursales": sucursales})

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

@login_required
def lista_asistencias(request):  
    return render(request, "lista_asistencias.html")

#Reporte de Horas
@login_required
def reporte_horas(request):
    """Muestra la página principal para generar reportes."""
    sucursales = Sucursal.objects.all()
    return render(request, "reporte_horas.html", {"sucursales": sucursales})

@require_http_methods(["GET"])
def health_check(request):
    """Endpoint para verificar el estado del servicio."""
    return JsonResponse({'status': 'healthy'}, status=200)

# --- API PARA EL REPORTE (VERSIÓN FINAL) ---
@login_required
@require_http_methods(["GET"])
def api_reporte_horas(request):
    """
    API que recibe la petición, la pasa al orquestador en main.py y devuelve el resultado.
    """
    try:
        start_date = request.GET.get("startDate")
        end_date = request.GET.get("endDate") 
        sucursal = request.GET.get("sucursal", "Todas")
        
        print(f"📋 Petición recibida para la sucursal: {sucursal}, Fechas: {start_date} a {end_date}")

        if not start_date or not end_date:
            return JsonResponse({"error": "Debe proporcionar fecha de inicio y fin."}, status=400)

        device_map = {
            "Todas": "%", "Villas": "%villas%", "31pte": "%31pte%", 
            "Nave": "%nave%", "RioBlanco": "%rioblanco%"
        }
        device_filter = device_map.get(sucursal, "%")

        # Llamada única al orquestador en main.py
        resultado = generar_reporte_completo(
            start_date=start_date,
            end_date=end_date,
            sucursal=sucursal,
            device_filter=device_filter
        )
        
        if not resultado.get("success"):
            return JsonResponse({"error": resultado.get("error", "Error desconocido")}, status=500)

        return JsonResponse(resultado)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": f"Error interno del servidor: {str(e)}"}, status=500)

