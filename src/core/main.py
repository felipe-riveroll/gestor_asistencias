# main.py

from datetime import datetime
from typing import List, Dict
import os
from dotenv import load_dotenv
import pandas as pd

from .api_client import APIClient, procesar_permisos_empleados
# Se importan la clase y las nuevas funciones de services
from .services import AttendanceProcessor, calcular_metricas_adicionales, agregar_datos_dashboard_por_sucursal
from .models import Empleado
from .services import calcular_metricas_adicionales, agregar_datos_dashboard_por_sucursal # Asegúrate que estén importadas

class AttendanceReportManager:
    """Clase de ayuda para obtener datos, ya no genera el reporte directamente."""
    def __init__(self):
        """ ✅ CORREGIDO: Constructor usa doble guion bajo __init__ """
        self.api_client = APIClient()
    
    def _prepare_report_data(self, start_date: str, end_date: str, sucursal: str):
        """Método unificado para obtener datos base para cualquier reporte."""
        load_dotenv()
        if not all([os.getenv("ASIATECH_API_KEY"), os.getenv("ASIATECH_API_SECRET")]):
            raise ValueError("Credenciales de API no configuradas")

        if sucursal != 'Todas':
            """ ✅ CORREGIDO: Filtro de Django usa doble guion bajo __ """
            empleados = Empleado.objects.filter(asignaciones__sucursal__nombre_sucursal=sucursal).distinct()
        else:
            empleados = Empleado.objects.all()
            
        # CÓDIGO CORREGIDO (ASEGÚRATE DE QUE QUEDE ASÍ):
        codigos_empleados = [str(emp.codigo_frappe) for emp in empleados if emp.codigo_frappe is not None]
        
        device_map = {"Villas": "%villas%", "31pte": "%31pte%", "Nave": "%nave%", "RioBlanco": "%rioblanco%"}

        device_filter = device_map.get(sucursal, "%")

        checkin_records = self.api_client.fetch_checkins(start_date, end_date, device_filter)
        leave_records = self.api_client.fetch_leave_applications(start_date, end_date)
        permisos_dict = procesar_permisos_empleados(leave_records)

        return codigos_empleados, checkin_records, permisos_dict

# --- FUNCIONES ORQUESTADORAS (REPORTES ACTUALES - SIN CAMBIOS) ---

def generar_reporte_completo(start_date: str, end_date: str, sucursal: str) -> dict:
    """Orquestador para el Reporte de Horas (Resumen)."""
    try:
        manager = AttendanceReportManager()
        processor = AttendanceProcessor()
        
        codigos, checkins, permisos = manager._prepare_report_data(start_date, end_date, sucursal)
        if not codigos:
            return {"success": True, "data": []}

        df_detalle, df_resumen = processor.procesar_reporte_completo(
            checkin_data=checkins,
            permisos_dict=permisos,
            start_date=start_date,
            end_date=end_date,
            employee_codes=codigos
        )
        return {"success": True, "data": df_resumen.to_dict('records')}
    except Exception as e:
        return {"success": False, "error": str(e)}

def generar_reporte_detalle_completo(start_date: str, end_date: str, sucursal: str) -> dict:
    """Orquestador para la Lista de Asistencias (Detalle)."""
    try:
        manager = AttendanceReportManager()
        processor = AttendanceProcessor()

        codigos, checkins, permisos = manager._prepare_report_data(start_date, end_date, sucursal)
        if not codigos:
            return {"success": True, "data": []}
            
        df_final = processor.procesar_reporte_detalle(
            checkin_data=checkins,
            permisos_dict=permisos,
            start_date=start_date,
            end_date=end_date,
            employee_codes=codigos
        )
        return {"success": True, "data": df_final.to_dict('records')}
    except Exception as e:
        return {"success": False, "error": str(e)}

# === NUEVA FUNCIÓN ORQUESTADORA PARA DASHBOARD GENERAL (ADOPTADA Y CORREGIDA) ===

def generar_datos_dashboard_general(start_date: str, end_date: str) -> dict:
    """
    Orquestador para dashboard: Agregados x Sucursal, Resumen Horas x Empleado, KPIs x Empleado.
    Adopta la lógica de tu compañero para retornar dos listas de KPIs y el nuevo KPI de Faltas Justificadas.
    """
    # Estructura vacía completa (para manejar errores y no-datos)
    empty_summary = {"total_attendances": 0, "total_permissions": 0, "total_absences": 0, "total_justified_absences": 0}
    empty_data = {"branches": [], "period_summary": empty_summary, "employee_summary_kpis": [], "employee_performance_kpis": []} # Dos listas

    try:
        manager = AttendanceReportManager()
        processor = AttendanceProcessor()

        # 1. Obtener datos
        print(f"[INFO Dashboard] Obteniendo datos {start_date} a {end_date}")
        codigos, checkins, permisos = manager._prepare_report_data(start_date, end_date, sucursal='Todas')
        if not codigos: return {"success": True, "data": empty_data}

        # 2. Procesar reportes
        print("[INFO Dashboard] Procesando reporte completo...")
        df_detalle, df_resumen = processor.procesar_reporte_completo(
            checkin_data=checkins, permisos_dict=permisos, start_date=start_date,
            end_date=end_date, employee_codes=codigos
        )
        if df_resumen.empty or df_detalle.empty: return {"success": True, "data": empty_data}
        
        # 3. Calcular métricas (Eficiencia, Puntualidad, SIC, Tasa Ausentismo)
        # Esto genera df_metricas con columnas en ESPAÑOL
        print("[INFO Dashboard] Calculando métricas adicionales...")
        df_metricas = calcular_metricas_adicionales(df_resumen.copy(), df_detalle.copy())

        # 4. Agregar por sucursal
        print("[INFO Dashboard] Agregando datos por sucursal...")
        datos_agregados = agregar_datos_dashboard_por_sucursal(df_metricas.copy())

        # 5. Calcular resumen del periodo (Lógica adoptada de tu compañero)
        print("[INFO Dashboard] Calculando resumen del periodo...")
        # Lógica más precisa del compañero para asistencias (días con horario, chequeo, y sin permiso)
        total_attendances = int(df_detalle[(df_detalle['horas_esperadas'].dt.total_seconds() > 0) & (df_detalle['checados_count'] > 0) & (df_detalle['tiene_permiso'] == False)].shape[0])
        total_permissions = int(df_detalle['tiene_permiso'].sum()) # Días con permiso (justificados o no)
        total_absences = int(df_resumen['faltas_del_periodo'].sum()) if 'faltas_del_periodo' in df_resumen.columns else 0 # Injustificadas
        total_justified_absences = int(df_resumen['faltas_justificadas'].sum()) if 'faltas_justificadas' in df_resumen.columns else 0 # Justificadas

        period_summary = { 
            "total_attendances": total_attendances, 
            "total_permissions": total_permissions, # Esto se usa para gráficos
            "total_absences": total_absences,
            "total_justified_absences": total_justified_absences # NUEVO KPI
        }
        print(f"[INFO Dashboard] Resumen Periodo: {period_summary}")

        # 6. ✅ Preparar KPIs - Lista 1: Resumen de Horas (Hrs Trab, Planif, Var, Ret, Aus)
        print("[INFO Dashboard] Preparando Resumen Horas por Empleado...")
        
        # Columnas necesarias del DF_RESUMEN para esta tabla
        summary_cols_needed = ['employee', 'Nombre', 'total_horas_trabajadas', 'total_horas', 'diferencia_HHMMSS', 'total_retardos', 'faltas_del_periodo']
        
        # Dado que df_metricas tiene las columnas renombradas, usamos df_resumen para la data sin renombrar
        # o df_metricas y renombramos solo esta subselección
        df_summary_kpis = df_resumen.copy()
        
        # Renombrar para coincidir con el front-end
        summary_rename_map = {
            'employee': 'ID',
            'Nombre': 'Empleado',
            'total_horas_trabajadas': 'Hrs. Trabajadas',
            'total_horas': 'Hrs. Planificadas', # Horas esperadas netas
            'diferencia_HHMMSS': 'Variación',
            'total_retardos': 'Retardos',
            'faltas_del_periodo': 'Ausencias' # Faltas injustificadas
        }
        
        # Filtra solo las columnas necesarias para esta tabla
        final_summary_cols = ['ID', 'Empleado', 'Hrs. Trabajadas', 'Hrs. Planificadas', 'Variación', 'Retardos', 'Ausencias']
        
        # Aplicamos renombrado
        df_summary_kpis = df_summary_kpis.rename(columns=summary_rename_map)
        
        # Limpiamos y ordenamos
        df_summary_kpis = df_summary_kpis[list(set(final_summary_cols).intersection(df_summary_kpis.columns))]
        summary_kpis_list = df_summary_kpis.to_dict('records')
        print(f"[INFO Dashboard] Resumen Horas preparado para {len(summary_kpis_list)} empleados.")

        # 7. ✅ Preparar KPIs - Lista 2: Rendimiento (Tasa Aus, Punt, Efic, SIC)
        print("[INFO Dashboard] Preparando KPIs de Rendimiento por Empleado...")
        
        # Columnas necesarias del DF_METRICAS (que ya están en ESPAÑOL)
        perf_cols_needed = ['ID', 'Nombre', 'Tasa Ausentismo (%)', 'Índice Puntualidad (%)', 'Eficiencia Horas (%)', 'SIC']
        
        df_performance_kpis = df_metricas.copy()
        
        # Aseguramos que solo usamos las columnas de KPIs de rendimiento
        existing_perf_cols = [col for col in perf_cols_needed if col in df_performance_kpis.columns]
        df_performance_kpis = df_performance_kpis[existing_perf_cols]
        
        # Redondeo final a 1 decimal (Ya se redondeó en services.py a 1, solo para asegurar el tipo)
        performance_kpis_list = df_performance_kpis.round(1).to_dict('records') 
        print(f"[INFO Dashboard] KPIs Rendimiento preparados para {len(performance_kpis_list)} empleados.")

        # 8. Estructura final JSON con AMBAS listas
        final_data = {
            "branches": datos_agregados,
            "period_summary": period_summary,
            "employee_summary_kpis": summary_kpis_list,        # <-- Lista 1 (Resumen Horas)
            "employee_performance_kpis": performance_kpis_list  # <-- Lista 2 (Rendimiento)
        }
        print("[INFO Dashboard] Datos finales listos para enviar.")
        return {"success": True, "data": final_data}

    except Exception as e:
        import traceback
        print(f"[ERROR Dashboard General]: Ocurrió una excepción - {e}")
        traceback.print_exc()
        return {"success": False, "error": f"Error interno: {str(e)}", "data": empty_data}