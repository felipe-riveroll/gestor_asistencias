from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.http import JsonResponse
from .services import autenticar_usuario, crear_empleado_service, crear_horario_service
from .models import Sucursal, Horario, Empleado, AsignacionHorario, DiaSemana, ResumenHorario
from .api_client import APIClient
from datetime import datetime, timedelta
from django.db.models import Prefetch
import traceback
import pandas as pd


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
def gestion_usuarios(request):
    return render(request, "gestion_usuarios.html")

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
        data = request.POST
        try:
            crear_empleado_service(data)
            messages.success(request, "Empleado creado correctamente.")
        except Exception as e:
            messages.error(request, "Error al crear empleado.")
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
        return redirect("admin-gestion-empleados")  # ajusta a tu URL de lista
    return render(request, "admin-gestion-empleados")

@login_required
def lista_asistencias(request):
    return render(request, "lista_asistencias.html")

#Api reporte horas
# ✅ NUEVA FUNCIÓN PARA LA API (AGREGAR ANTES de reporte_horas)
@login_required
@require_http_methods(["GET", "POST"])
def api_reporte_horas(request):
    """
    API para generar reporte de horas - VERSIÓN DEFINITIVA
    """
    
    def _calcular_diferencia_simple(horas_trabajadas, horas_esperadas):
        try:
            def time_to_minutes(time_str):
                try:
                    if pd.isna(time_str) or time_str in ['NaT', '00:00:00']:
                        return 0
                    parts = time_str.split(':')
                    if len(parts) >= 2:
                        return int(parts[0]) * 60 + int(parts[1])
                    return 0
                except:
                    return 0
            
            trab_min = time_to_minutes(horas_trabajadas)
            esp_min = time_to_minutes(horas_esperadas)
            diferencia = esp_min - trab_min
            signo = "-" if diferencia < 0 else ""
            abs_diff = abs(diferencia)
            horas = abs_diff // 60
            minutos = abs_diff % 60
            return f"{signo}{horas:02d}:{minutos:02d}:00"
        except:
            return "00:00:00"
    
    try:
        print("=" * 60)
        print("✅ API reporte_horas INICIADA - VERSIÓN DEFINITIVA")
        print("=" * 60)
        
        # SOPORTE PARA GET Y POST
        if request.method == 'POST':
            fecha_inicio = request.POST.get("startDate")
            fecha_fin = request.POST.get("endDate")
            sucursal = request.POST.get("sucursal", "Todas")
            empleado = request.POST.get("empleado", "")
            metodo = "POST"
        else:
            fecha_inicio = request.GET.get("startDate")
            fecha_fin = request.GET.get("endDate") 
            sucursal = request.GET.get("sucursal", "Todas")
            empleado = request.GET.get("empleado", "")
            metodo = "GET"
        
        print(f"📋 Parámetros recibidos ({metodo}):")
        print(f"   - startDate: {fecha_inicio}")
        print(f"   - endDate: {fecha_fin}") 
        print(f"   - sucursal: {sucursal}")
        print(f"   - empleado: {empleado}")

        if not fecha_inicio or not fecha_fin:
            return JsonResponse({"error": "Debe proporcionar fecha de inicio y fin."}, status=400)

        # Obtener datos de la API
        try:
            # Importar también procesar_permisos_empleados
            from .api_client import APIClient, procesar_permisos_empleados
            client = APIClient()
            print("✅ APIClient importado correctamente")
            
            device_map = {
                "Todas": "%", "Villas": "Villas%", "31pte": "31pte%", 
                "Nave": "Nave%", "RioBlanco": "RioBlanco%"
            }
            device_filter = device_map.get(sucursal, "%")
            print(f"🔍 Device filter: {device_filter}")
            #CAMBIOS AQUI O SI
            print("📄 Obteniendo permisos de la API...")
            permisos_data = client.fetch_leave_applications(fecha_inicio, fecha_fin)
            permisos_dict = procesar_permisos_empleados(permisos_data)
            print(f"✅ Permisos procesados. {len(permisos_dict)} empleados con permisos encontrados.")
            #---------------------------------------------
            print("📡 Obteniendo checadas de la API...")
            checkins = client.fetch_checkins(fecha_inicio, fecha_fin, device_filter)
            print(f"✅ Checadas obtenidas: {len(checkins)}")
            
            if not checkins:
                return JsonResponse({"data": []})

        except Exception as e:
            print(f"❌ Error en APIClient: {e}")
            return JsonResponse({"error": f"Error al obtener datos: {str(e)}"}, status=500)

        # Procesar con AttendanceProcessor
        try:
            #aqui un poquito de cambio xd
            from .services import AttendanceProcessor
            processor = AttendanceProcessor()
            print("✅ AttendanceProcessor importado correctamente")
            
            print("🔄 Creando DataFrame...")
            df = processor.process_checkins_to_dataframe(checkins, fecha_inicio, fecha_fin)
            
            if df.empty:
                return JsonResponse({"data": []})
                
            print(f"✅ DataFrame creado: {len(df)} filas")
            #----------------------------------------
            cache_horarios = {}
            df = processor.analizar_asistencia_con_horarios_cache(df, cache_horarios)
            #CAMBIOS AQUI O SI
            df = processor.ajustar_horas_esperadas_con_permisos(df, permisos_dict, cache_horarios)
            print("✅ Lógica de descuento por permisos aplicada.")
            #-------------------
            # ▼▼▼ AÑADE ESTA LÍNEA AQUÍ ▼▼▼
            df = processor.clasificar_faltas_con_permisos(df)
        # ▲▲▲ FIN DE LA LÍNEA A AÑADIR ▲▲▲
            df = processor.aplicar_calculo_horas_descanso(df)
            df_totales = processor.calcular_totales_por_empleado(df)

        except Exception as e:
            print(f"❌ Error en AttendanceProcessor: {e}")
            return JsonResponse({"error": f"Error al procesar datos: {str(e)}"}, status=500)

        # Convertir a formato para frontend
        print("🔄 Convirtiendo a formato frontend...")
        resultados = []
        
        for index, row in df_totales.iterrows():
            try:
                horas_trabajadas = str(row.get("total_horas_trabajadas", "00:00:00"))
                horas_esperadas = str(row.get("total_horas_esperadas", "00:00:00"))
                horas_descanso = str(row.get("total_horas_descanso", "00:00:00"))
                total_horas = str(row.get("total_horas", "00:00:00"))
                
                # Asegurar formato HH:MM:SS
                for field in [horas_trabajadas, horas_esperadas, horas_descanso, total_horas]:
                    if len(field.split(':')) == 2:
                        field += ":00"
                
                resultado = {
                    "employee": str(row.get("employee", "")),
                    "Nombre": str(row.get("Nombre", "Sin nombre")),
                    "total_horas_trabajadas": horas_trabajadas,
                    "total_horas_esperadas": horas_esperadas,
                    #aqui tambien lo cambie nada mas esa linea xd
                    "total_horas_descontadas_permiso": str(row.get("total_horas_descontadas_permiso", "00:00:00")),
                    #--------------------------------
                    "total_horas_descanso": horas_descanso,
                    "total_horas": total_horas,
                    "total_retardos": str(row.get("total_retardos", "0")),
                    "faltas_del_periodo": str(row.get("total_faltas", "0")),
                    "faltas_justificadas": str(row.get("faltas_justificadas", "0")),
                    "total_faltas": str(row.get("total_faltas", "0")),
                    "episodios_ausencia": str(row.get("episodios_ausencia", "0")),
                    "total_salidas_anticipadas": str(row.get("total_salidas_anticipadas", "0")),
                    "diferencia_HHMMSS": str(row.get("diferencia_HHMMSS", "00:00:00"))
                }
                resultados.append(resultado)
                
            except Exception as e:
                print(f"⚠️ Error procesando fila {index}: {e}")
                continue

        # Filtrar por empleado
        if empleado:
            original_count = len(resultados)
            resultados = [r for r in resultados 
                         if empleado and empleado.lower() in r.get('Nombre', '').lower()]
            print(f"🔍 Filtrado por empleado: {original_count} → {len(resultados)}")

        print(f"✅ Procesamiento completado: {len(resultados)} registros")
        return JsonResponse({"data": resultados})

    except Exception as e:
        print("❌ ERROR GENERAL en api_reporte_horas:")
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": "Error interno del servidor"}, status=500)

            # En tu función api_reporte_horas, justo antes del return JsonResponse
        print("🔍 VERIFICACIÓN FINAL - DATOS ENVIADOS AL FRONTEND:")
        if resultados and len(resultados) > 0:
            primer_registro = resultados[0]
            print("📊 PRIMER REGISTRO COMPLETO:")
            for key, value in primer_registro.items():
                print(f"   - {key}: {value}")
            
            print(f"📈 TOTAL REGISTROS: {len(resultados)}")
            print(f"🔢 TOTAL COLUMNAS: {len(primer_registro.keys())}")

# ✅ FUNCIÓN EXISTENTE PARA MOSTRAR TEMPLATE (DEJAR COMO ESTÁ)
@login_required
def reporte_horas(request):
    return render(request, "reporte_horas.html")