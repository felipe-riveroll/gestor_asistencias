from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.http import JsonResponse
from .services import autenticar_usuario, crear_empleado_service, crear_horario_service,AttendanceProcessor, generar_reporte_asistencia
from .models import Sucursal, Horario, Empleado, AsignacionHorario, DiaSemana, ResumenHorario
from .api_client import APIClient
from datetime import datetime, timedelta
from django.db.models import Prefetch
import traceback
import pandas as pd
import time
import gc
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

@login_required
def lista_asistencias(request):  # ← NOMBRE CORREGIDO
    return render(request, "lista_asistencias.html")

# Health check endpoint
@require_http_methods(["GET"])
def health_check(request):
    """Endpoint para verificar el estado del servicio"""
    try:
        from django.db import connection
        # Verificar base de datos
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return JsonResponse({
            'status': 'healthy',
            'timestamp': time.time(),
            'database': 'connected'
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'timestamp': time.time(),
            'database': 'disconnected',
            'error': str(e)
        }, status=503)


# Api reporte horas - VERSIÓN DEFINITIVA CORREGIDA
@login_required
@require_http_methods(["GET", "POST"])
def api_reporte_horas(request):
    """
    API para generar reporte de horas - VERSIÓN SIMPLIFICADA CON ORCHESTRATOR
    """
    try:
        print("=" * 60)
        print("✅ API reporte_horas INICIADA - USANDO MAIN.PY")
        print("=" * 60)
        
        # SOPORTE PARA GET Y POST
        if request.method == 'POST':
            fecha_inicio = request.POST.get("startDate")
            fecha_fin = request.POST.get("endDate")
            sucursal = request.POST.get("sucursal", "Todas")
            empleado = request.POST.get("empleado", "")
        else:
            fecha_inicio = request.GET.get("startDate")
            fecha_fin = request.GET.get("endDate") 
            sucursal = request.GET.get("sucursal", "Todas")
            empleado = request.GET.get("empleado", "")

        print(f"📋 Parámetros recibidos:")
        print(f"   - startDate: {fecha_inicio}")
        print(f"   - endDate: {fecha_fin}") 
        print(f"   - sucursal: {sucursal}")
        print(f"   - empleado: {empleado}")

        # Validación de parámetros
        if not fecha_inicio or not fecha_fin:
            return JsonResponse({"error": "Debe proporcionar fecha de inicio y fin."}, status=400)

        # Mapeo de sucursales a device filters
        device_map = {
            "Todas": "%", 
            "Villas": "Villas%", 
            "31pte": "31pte%", 
            "Nave": "Nave%", 
            "RioBlanco": "RioBlanco%"
        }
        device_filter = device_map.get(sucursal, "%")
        print(f"🔍 Device filter: {device_filter}")

        # ✅ USAR LA FUNCIÓN DESDE MAIN.PY
        print("🔄 Ejecutando main.generar_reporte_completo...")
        resultado = generar_reporte_completo(
            start_date=fecha_inicio,
            end_date=fecha_fin,
            sucursal=sucursal,
            device_filter=device_filter
        )

        if not resultado["success"]:
            print(f"❌ Error de main.py: {resultado['error']}")
            return JsonResponse({"error": resultado["error"]}, status=500)

        print(f"✅ Main.py completado: {len(resultado['data'])} empleados procesados")

        # Filtrar por empleado si se especificó
        datos_filtrados = resultado["data"]
        if empleado and empleado.strip():
            original_count = len(datos_filtrados)
            datos_filtrados = [
                r for r in resultado["data"] 
                if (empleado.lower() in r.get('Nombre', '').lower() or 
                    empleado.lower() in r.get('employee', '').lower())
            ]
            print(f"🔍 Filtrado por empleado: {original_count} → {len(datos_filtrados)}")

        return JsonResponse({
            "data": datos_filtrados,
            "metadata": {
                "total_registros": len(datos_filtrados),
                "rango_fechas": f"{fecha_inicio} a {fecha_fin}",
                "sucursal": sucursal,
                "empleado_filtrado": empleado if empleado else "Todos",
                **resultado.get("metadata", {})
            }
        })

    except Exception as e:
        print("❌ ERROR GENERAL en api_reporte_horas:")
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": f"Error interno del servidor: {str(e)}"}, status=500)

# ✅ FUNCIÓN EXISTENTE PARA MOSTRAR TEMPLATE
@login_required
def reporte_horas(request):
    return render(request, "reporte_horas.html")
