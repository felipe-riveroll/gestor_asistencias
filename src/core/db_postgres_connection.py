"""
Conexión a BD PostgreSQL - VERSIÓN FINAL OPTIMIZADA Y SIMPLIFICADA
"""
from datetime import datetime, timedelta, time # Importar 'time' explícitamente
from typing import Dict, List
from django.db.models import Q, Case, When, IntegerField

from .models import Empleado, AsignacionHorario, DiaSemana

def obtener_horario_empleado_completo(employee_code: str, fecha: str = None) -> Dict:
    """
    Obtiene el horario de un solo empleado consultando las tablas directamente.
    """
    try:
        empleado_obj = Empleado.objects.get(codigo_frappe=employee_code)
    except Empleado.DoesNotExist:
        return _crear_horario_vacio(employee_code)

    es_primera_quincena = True
    if fecha:
        try:
            es_primera_quincena = datetime.strptime(fecha, '%Y-%m-%d').day <= 15
        except: pass
    
    horarios_detallados = {}
    dias_semana = DiaSemana.objects.all().order_by('dia_id')

    # Mapa de abreviaturas para descripciones de turno
    mapa_dia_abrev = {1: 'L', 2: 'M', 3: 'X', 4: 'J', 5: 'V', 6: 'S', 7: 'D'}

    for dia in dias_semana:
        # Lógica de filtrado para encontrar el turno correcto
        filtro_dia_general = Q()
        abrev_dia = mapa_dia_abrev.get(dia.dia_id)
        if abrev_dia:
            filtro_dia_general = Q(tipo_turno__descripcion__icontains=abrev_dia)
        
        # Casos especiales de rangos
        if dia.dia_id in range(1, 6): filtro_dia_general |= Q(tipo_turno__descripcion='L-V')
        if dia.dia_id in range(1, 5): filtro_dia_general |= Q(tipo_turno__descripcion='L-J')
        if dia.dia_id in range(2, 6): filtro_dia_general |= Q(tipo_turno__descripcion='M-V')
        
        # Construimos la consulta priorizada con el ORM
        asignacion = AsignacionHorario.objects.filter(
            Q(empleado=empleado_obj) & (Q(dia_especifico_id=dia.dia_id) | filtro_dia_general)
        ).annotate(
            prioridad=Case(
                When(dia_especifico_id=dia.dia_id, es_primera_quincena=es_primera_quincena, then=1),
                When(dia_especifico_id=dia.dia_id, es_primera_quincena__isnull=True, then=2),
                When(dia_especifico_id__isnull=True, es_primera_quincena=es_primera_quincena, then=3),
                When(dia_especifico_id__isnull=True, es_primera_quincena__isnull=True, then=4),
                default=5,
                output_field=IntegerField(),
            )
        ).select_related('horario', 'tipo_turno').order_by('prioridad').first()

        if asignacion:
            if asignacion.dia_especifico_id:
                entrada, salida, cruza = asignacion.hora_entrada_especifica, asignacion.hora_salida_especifica, asignacion.hora_salida_especifica_cruza_medianoche
            elif asignacion.horario:
                entrada, salida, cruza = asignacion.horario.hora_entrada, asignacion.horario.hora_salida, asignacion.horario.cruza_medianoche
            else:
                entrada, salida, cruza = None, None, False
            
            horarios_detallados[dia.nombre_dia] = {"entrada": entrada, "salida": salida, "cruza_medianoche": cruza, "tiene_horario": True}
        else:
            horarios_detallados[dia.nombre_dia] = {"tiene_horario": False}

    return _formatear_resultado_desde_python(horarios_detallados, empleado_obj)


def _formatear_resultado_desde_python(horarios_detallados: dict, empleado: Empleado) -> Dict:
    # ❌ ELIMINADA línea "from datetime import time" innecesaria por la importación al inicio.
    horas_totales_semana = 0.0
    
    primera_asignacion = empleado.asignaciones.select_related('sucursal').first()
    sucursal = primera_asignacion.sucursal.nombre_sucursal if primera_asignacion and primera_asignacion.sucursal else "N/A" # Añadir chequeo de sucursal

    for dia, info in horarios_detallados.items():
        if info.get("tiene_horario"):
            try:
                entrada, salida, cruza = info["entrada"], info["salida"], info["cruza_medianoche"]
                if not all([entrada, salida]): continue

                dummy_date = datetime.min
                # Conversión segura a datetime.time si no lo es
                entrada_t = entrada if isinstance(entrada, time) else datetime.strptime(str(entrada), '%H:%M:%S').time()
                salida_t = salida if isinstance(salida, time) else datetime.strptime(str(salida), '%H:%M:%S').time()
                
                entrada_dt = datetime.combine(dummy_date.date(), entrada_t)
                salida_dt = datetime.combine(dummy_date.date(), salida_t)

                # 🟢 CORRECCIÓN DE CÁLCULO PARA TURNOS NOCTURNOS
                # Si cruza medianoche, sumamos 1 día a la hora de salida para la resta.
                # También se añade la lógica de comparación de tiempo para más robustez.
                if cruza or salida_dt < entrada_dt:
                    diferencia = (salida_dt + timedelta(days=1)) - entrada_dt
                else:
                    diferencia = salida_dt - entrada_dt
                
                horas_totales_dia = diferencia.total_seconds() / 3600.0
                horas_totales_dia = round(horas_totales_dia, 2) # Aplicamos redondeo
                
                info["horas_totales"] = horas_totales_dia
                horas_totales_semana += horas_totales_dia
            except Exception as e:
                # print(f"Error calculando horas para {empleado.codigo_frappe} en {dia}: {e}") # Debug opcional
                info["tiene_horario"] = False

    dias_con_horario = sum(1 for info in horarios_detallados.values() if info.get("tiene_horario"))

    if dias_con_horario == 0:
        return _crear_horario_vacio(empleado.codigo_frappe)

    return {
        'empleado_id': empleado.codigo_frappe,
        'sucursal': sucursal,
        'dias_con_horario': dias_con_horario,
        'horarios_detallados': horarios_detallados,
        'horas_por_dia': round(horas_totales_semana / dias_con_horario, 2) if dias_con_horario > 0 else 0
    }

def _crear_horario_vacio(employee_code=None) -> Dict:
    print(f"⚠️  Empleado {employee_code} sin horario válido en la base de datos.")
    return {'dias_con_horario': 0}