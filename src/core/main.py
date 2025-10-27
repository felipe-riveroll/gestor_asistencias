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

class AttendanceReportManager:
    """Clase de ayuda para obtener datos, ya no genera el reporte directamente."""
    def __init__(self):
        self.api_client = APIClient()
    
    def _prepare_report_data(self, start_date: str, end_date: str, sucursal: str):
        """Método unificado para obtener datos base para cualquier reporte."""
        load_dotenv()
        if not all([os.getenv("ASIATECH_API_KEY"), os.getenv("ASIATECH_API_SECRET")]):
            raise ValueError("Credenciales de API no configuradas")

        if sucursal != 'Todas':
            empleados = Empleado.objects.filter(asignaciones__sucursal__nombre_sucursal=sucursal).distinct()
        else:
            empleados = Empleado.objects.all()
            
        codigos_empleados = [str(emp.codigo_frappe) for emp in empleados if emp.codigo_frappe]

        device_map = {"Villas": "%villas%", "31pte": "%31pte%", "Nave": "%nave%", "RioBlanco": "%rioblanco%"}
        device_filter = device_map.get(sucursal, "%")

        checkin_records = self.api_client.fetch_checkins(start_date, end_date, device_filter)
        leave_records = self.api_client.fetch_leave_applications(start_date, end_date)
        permisos_dict = procesar_permisos_empleados(leave_records)

        return codigos_empleados, checkin_records, permisos_dict

# --- FUNCIONES ORQUESTADORAS ---

def generar_reporte_completo(start_date: str, end_date: str, sucursal: str) -> dict:
    """Orquestador para el Reporte de Horas (Resumen)."""
    try:
        manager = AttendanceReportManager()
        processor = AttendanceProcessor()
        
        codigos, checkins, permisos = manager._prepare_report_data(start_date, end_date, sucursal)
        if not codigos:
            return {"success": True, "data": []}

        # La lógica de procesamiento ahora la llama directamente main.py
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

# === NUEVA FUNCIÓN ORQUESTADORA PARA DASHBOARD GENERAL ===

def generar_datos_dashboard_general(start_date: str, end_date: str) -> dict:
    """Orquestador para obtener los datos agregados por sucursal para el dashboard general."""
    try:
        manager = AttendanceReportManager()
        processor = AttendanceProcessor()
        
        # 1. Obtener datos de todas las sucursales
        codigos, checkins, permisos = manager._prepare_report_data(start_date, end_date, sucursal='Todas')
        if not codigos:
            return {"success": True, "data": {"branches": []}}

        # 2. Procesar los reportes para obtener dataframes de detalle y resumen
        df_detalle, df_resumen = processor.procesar_reporte_completo(
            checkin_data=checkins,
            permisos_dict=permisos,
            start_date=start_date,
            end_date=end_date,
            employee_codes=codigos
        )

        if df_resumen.empty:
            return {"success": True, "data": {"branches": []}}

        # 3. Calcular métricas avanzadas (Eficiencia, Puntualidad, Bradford)
        df_metricas = calcular_metricas_adicionales(df_resumen, df_detalle)

        # 4. Agregar los datos por sucursal
        datos_agregados = agregar_datos_dashboard_por_sucursal(df_metricas)

        # 5. Estructurar la respuesta final como la espera el frontend
        return {"success": True, "data": {"branches": datos_agregados}}

    except Exception as e:
        print(f"[ERROR Dashboard General]: {e}") # Log para debugging
        return {"success": False, "error": str(e)}