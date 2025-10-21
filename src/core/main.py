"""
Main orchestration script - VERSIÓN FINAL Y DEFINITIVA
"""
from datetime import datetime
from typing import List, Dict
import os
from dotenv import load_dotenv
import pandas as pd

from .api_client import APIClient, procesar_permisos_empleados
from .services import generar_reporte_asistencia
from .models import Empleado

class AttendanceReportManager:
    def __init__(self):
        self.api_client = APIClient()
    
    def validate_api_credentials(self) -> bool:
        load_dotenv()
        if not all([os.getenv("ASIATECH_API_KEY"), os.getenv("ASIATECH_API_SECRET")]):
            return False
        return True

    def validate_input_parameters(self, start_date: str, end_date: str):
        if not all([start_date, end_date]):
             raise ValueError("Las fechas de inicio y fin son requeridas.")
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
        if start_date > end_date:
            raise ValueError("La fecha de inicio no puede ser mayor a la fecha fin")

    def obtener_empleados_por_sucursal(self, sucursal: str) -> List[str]:
        print(f"🔍 Buscando a TODOS los empleados para la sucursal: {sucursal}")
        
        if sucursal == 'Todas':
            empleados = Empleado.objects.all()
        else:
            empleados = Empleado.objects.filter(
                asignaciones__sucursal__nombre_sucursal=sucursal
            ).distinct()
            
        codigos_empleados = [str(emp.codigo_frappe) for emp in empleados if emp.codigo_frappe]
        print(f"📋 Obtenidos {len(codigos_empleados)} empleados para el reporte.")
        return codigos_empleados

    def generate_attendance_report(self, start_date: str, end_date: str, sucursal: str, device_filter: str) -> dict:
        print(f"\n🚀 Iniciando reporte para {sucursal} ({start_date} a {end_date})...")
        try:
            self.validate_input_parameters(start_date, end_date)
            if not self.validate_api_credentials():
                return {"success": False, "error": "Credenciales de API no configuradas"}

            codigos_empleados = self.obtener_empleados_por_sucursal(sucursal)
            if not codigos_empleados:
                return {"success": True, "data": [], "metadata": {"total_empleados": 0}}

            checkin_records = self.api_client.fetch_checkins(start_date, end_date, device_filter)
            leave_records = self.api_client.fetch_leave_applications(start_date, end_date)
            permisos_dict = procesar_permisos_empleados(leave_records)

            print("\n📊 Procesando datos de asistencia...")
            df_detalle, df_resumen = generar_reporte_asistencia(
                checkin_data=checkin_records,
                permisos_dict=permisos_dict,
                joining_dates_dict={},
                start_date=start_date,
                end_date=end_date,
                employee_codes=codigos_empleados
            )

            if df_resumen.empty and codigos_empleados:
                 print("⚠️  El DataFrame de resumen está vacío, construyendo a partir de la lista de empleados.")
                 df_resumen = pd.DataFrame(codigos_empleados, columns=['employee'])
                 employee_map = {str(e.codigo_frappe): f"{e.nombre} {e.apellido_paterno}" for e in Empleado.objects.all()}
                 df_resumen['Nombre'] = df_resumen['employee'].map(employee_map)

            resultados_frontend = self._format_for_frontend(df_resumen)
            print("\n🎉 ¡Proceso completado!")
            
            return {
                "success": True,
                "data": resultados_frontend,
                "metadata": {"total_empleados": len(df_resumen)}
            }
        except Exception as e:
            import traceback; traceback.print_exc()
            return {"success": False, "error": str(e)}

    def _format_for_frontend(self, df_resumen: pd.DataFrame) -> List[Dict]:
        df_resumen = df_resumen.copy()
        columnas_esperadas = [
            'employee', 'Nombre', 'Sucursal', 'total_horas_trabajadas', 'total_horas_esperadas', 
            'total_horas_descontadas_permiso', 'total_horas_descanso', 'total_horas',
            'diferencia_HHMMSS', 'total_faltas', 'total_retardos', 'total_salidas_anticipadas'
        ]
        for col in columnas_esperadas:
            if col not in df_resumen.columns:
                if 'total' in col or 'faltas' in col: df_resumen[col] = 0
                else: df_resumen[col] = 'N/A'
        
        for col in df_resumen.columns:
            if 'int' in str(df_resumen[col].dtype) or 'float' in str(df_resumen[col].dtype):
                df_resumen[col] = df_resumen[col].fillna(0)
            else:
                df_resumen[col] = df_resumen[col].fillna('')

        return df_resumen.to_dict('records')

def generar_reporte_completo(start_date: str, end_date: str, sucursal: str, device_filter: str) -> dict:
    manager = AttendanceReportManager()
    return manager.generate_attendance_report(start_date, end_date, sucursal, device_filter)