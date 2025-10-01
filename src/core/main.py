"""
Main orchestration script for the attendance reporting system.
This script coordinates all modules to generate comprehensive attendance reports.
"""

from datetime import datetime
import sys
import pandas as pd
from typing import Dict, List, Tuple
import traceback
import os
from dotenv import load_dotenv

# ✅ IMPORTS CORRECTOS - desde services.py
from .api_client import APIClient, procesar_permisos_empleados
from .services import AttendanceProcessor, generar_reporte_asistencia
from .db_postgres_connection import obtener_horario_empleado_completo, format_complete_schedule_result


class AttendanceReportManager:
    """Main class that orchestrates the entire attendance reporting process."""
    
    def __init__(self):
        """Initialize the report manager with all required components."""
        self.api_client = APIClient()
        self.processor = AttendanceProcessor()
    
    def determine_period_type(self, start_date: str, end_date: str) -> Tuple[bool, bool]:
        """
        Determine if the period includes first half, second half, or both.
        """
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        incluye_primera = any(d.day <= 15 for d in pd.date_range(start=start_dt, end=end_dt, freq='D'))
        incluye_segunda = any(d.day > 15 for d in pd.date_range(start=start_dt, end=end_dt, freq='D'))
        
        return incluye_primera, incluye_segunda
    
    def obtener_codigos_empleados_api(self, checkin_data: List[Dict]) -> List[str]:
        """
        Extract employee codes from API check-in data.
        """
        if not checkin_data:
            return []

        df_empleados = pd.DataFrame(checkin_data)[["employee"]].drop_duplicates()
        return list(df_empleados["employee"])
    
    def validate_api_credentials(self) -> bool:
        """
        Validate that API credentials are available.
        """
        load_dotenv()
        
        API_KEY = os.getenv("ASIATECH_API_KEY")
        API_SECRET = os.getenv("ASIATECH_API_SECRET")
        
        if not all([API_KEY, API_SECRET]):
            print("❌ Error: Faltan credenciales de API (ASIATECH_API_KEY, ASIATECH_API_SECRET)")
            return False
        
        return True

    def validate_input_parameters(self, start_date: str, end_date: str, sucursal: str, device_filter: str):
        """Validar parámetros de entrada"""
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Formato de fecha inválido. Use YYYY-MM-DD")
        
        if not sucursal or not device_filter:
            raise ValueError("Sucursal y device_filter son requeridos")
        
        if start_date > end_date:
            raise ValueError("La fecha de inicio no puede ser mayor a la fecha fin")

    def obtener_horarios_desde_bd(self, sucursal: str, codigos_empleados: List[str], 
                                incluye_primera: bool, incluye_segunda: bool) -> Dict:
        """
        Obtener horarios usando las funciones que SÍ existen en db_postgres_connection
        """
        print(f"📋 Obteniendo horarios para {len(codigos_empleados)} empleados de {sucursal}")
        
        try:
            cache_horarios = {}
            
            # Para cada empleado, obtener su horario usando la función que SÍ existe
            for employee_code in codigos_empleados:
                try:
                    # Usar la función que SÍ existe: obtener_horario_empleado_completo
                    horario_completo = obtener_horario_empleado_completo(str(employee_code))
                    
                    if horario_completo and 'horas_por_dia' in horario_completo:
                        cache_horarios[employee_code] = horario_completo
                        print(f"   ✅ {employee_code}: {horario_completo.get('horas_por_dia', 8.0)} horas/día")
                    else:
                        print(f"   ⚠️ {employee_code}: Sin horario específico, usando 8.0 horas/día")
                        # Fallback si no hay horario
                        cache_horarios[employee_code] = {
                            'horas_por_dia': 8.0,
                            'horarios_detallados': {},
                            'fuente': 'fallback'
                        }
                        
                except Exception as e:
                    print(f"   ❌ Error obteniendo horario para {employee_code}: {e}")
                    # Fallback en caso de error
                    cache_horarios[employee_code] = {
                        'horas_por_dia': 8.0,
                        'horarios_detallados': {},
                        'fuente': 'error_fallback'
                    }
            
            print(f"✅ Horarios obtenidos para {len(cache_horarios)} empleados")
            return cache_horarios
            
        except Exception as e:
            print(f"❌ Error general obteniendo horarios: {e}")
            return {}

    def _execute_processing_steps(self, start_date: str, end_date: str, sucursal: str, device_filter: str):
        """Ejecutar pasos de procesamiento con manejo individual de errores"""
        results = {}
        
        # Paso 1: Fetch check-ins
        print("🔧 Ejecutando paso: fetch_checkins")
        results["checkin_records"] = self.api_client.fetch_checkins(start_date, end_date, device_filter)
        
        if not results["checkin_records"]:
            raise Exception("No se obtuvieron registros de entrada/salida")
        
        # Paso 2: Obtener códigos de empleados
        codigos_empleados = self.obtener_codigos_empleados_api(results["checkin_records"])
        print(f"✅ Se obtuvieron {len(results['checkin_records'])} registros para {len(codigos_empleados)} empleados")
        
        # Paso 3: Fetch leave applications
        print("🔧 Ejecutando paso: fetch_leaves")
        results["leave_records"] = self.api_client.fetch_leave_applications(start_date, end_date)
        results["permisos_dict"] = procesar_permisos_empleados(results["leave_records"])
        print(f"✅ Se procesaron permisos para {len(results['permisos_dict'])} empleados")
        
        # Paso 4: Determinar período y obtener horarios
        incluye_primera, incluye_segunda = self.determine_period_type(start_date, end_date)
        print(f"📅 Período incluye: {'1ra quincena' if incluye_primera else ''} {'2da quincena' if incluye_segunda else ''}")
        
        print("🔧 Ejecutando paso: fetch_schedules")
        results["cache_horarios"] = self.obtener_horarios_desde_bd(
            sucursal, codigos_empleados, incluye_primera, incluye_segunda
        )
        print(f"✅ Se cargaron horarios para {len(results['cache_horarios'])} empleados")
        
        return results

    def _build_success_response(self, resultados: List[Dict], df_detalle: pd.DataFrame, 
                              df_resumen: pd.DataFrame, start_date: str, end_date: str,
                              sucursal: str, cache_horarios: Dict, permisos_dict: Dict):
        """Construir respuesta exitosa estandarizada"""
        return {
            "success": True,
            "data": resultados,
            "metadata": {
                "total_empleados": len(df_resumen),
                "total_registros": len(df_detalle) if df_detalle is not None else 0,
                "periodo": f"{start_date} a {end_date}",
                "sucursal": sucursal,
                "empleados_con_horario": len(cache_horarios),
                "empleados_con_permisos": len(permisos_dict),
                "fecha_generacion": datetime.now().isoformat()
            }
        }

    def generate_attendance_report(
        self, 
        start_date: str, 
        end_date: str, 
        sucursal: str, 
        device_filter: str
    ) -> dict:
        """
        Main method to generate a complete attendance report.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            sucursal: Branch name
            device_filter: Device filter pattern (e.g., "%Villas%")
            
        Returns:
            Dictionary with report status and generated data
        """
        print(f"\n🚀 Iniciando reporte para {sucursal} ({start_date} a {end_date})...")
        
        try:
            # Validaciones iniciales
            self.validate_input_parameters(start_date, end_date, sucursal, device_filter)
            
            if not self.validate_api_credentials():
                return {"success": False, "error": "Credenciales de API no configuradas"}

            # Ejecutar pasos de procesamiento
            processing_results = self._execute_processing_steps(start_date, end_date, sucursal, device_filter)
            
            # Extraer resultados
            checkin_records = processing_results["checkin_records"]
            permisos_dict = processing_results["permisos_dict"]
            cache_horarios = processing_results["cache_horarios"]
            
            # Generar reporte final
            joining_dates_dict = {}  # Placeholder como en tu código original
            
            print("\n📊 Procesando datos de asistencia...")
            df_detalle, df_resumen = generar_reporte_asistencia(
                checkin_data=checkin_records,
                permisos_dict=permisos_dict,
                joining_dates_dict=joining_dates_dict,
                start_date=start_date,
                end_date=end_date
            )
            
            if df_resumen.empty:
                return {"success": False, "error": "No se pudo generar el resumen del reporte"}

            print(f"✅ Procesamiento completado: {len(df_resumen)} empleados en el resumen")

            # Convert DataFrames to the format expected by the frontend
            print("\n🔄 Formateando datos para frontend...")
            resultados_frontend = self._format_for_frontend(df_resumen)

            print("\n🎉 ¡Proceso completado!")
            
            return self._build_success_response(
                resultados_frontend, df_detalle, df_resumen, 
                start_date, end_date, sucursal, cache_horarios, permisos_dict
            )
            
        except Exception as e:
            error_msg = f"Error durante la generación del reporte: {str(e)}"
            print(f"❌ {error_msg}")
            traceback.print_exc()
            return {"success": False, "error": error_msg}

    def _format_for_frontend(self, df_resumen: pd.DataFrame) -> List[Dict]:
        """
        Format the summary DataFrame for frontend consumption.
        """
        if df_resumen.empty:
            return []

        resultados = []
        
        for index, row in df_resumen.iterrows():
            try:
                # Safe value extraction
                def safe_time_value(value, default="00:00:00"):
                    if pd.isna(value) or value is None or value == "":
                        return default
                    return str(value)
                
                def safe_int_value(value, default=0):
                    if pd.isna(value) or value is None:
                        return default
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return default
                
                # Format time values
                def formatear_tiempo(tiempo):
                    if not tiempo or tiempo == "00:00:00":
                        return "00:00:00"
                    
                    tiempo_str = str(tiempo)
                    
                    # Handle negative differences (like "-13:03:26")
                    if tiempo_str.startswith('-'):
                        signo = '-'
                        tiempo_str = tiempo_str[1:]
                    else:
                        signo = ''
                    
                    # Separate components
                    partes = tiempo_str.split(':')
                    
                    if len(partes) == 3:
                        # Already in HH:MM:SS format
                        horas, minutos, segundos = partes
                        return f"{signo}{int(horas):02d}:{int(minutos):02d}:{int(segundos):02d}"
                    elif len(partes) == 2:
                        # HH:MM format, add seconds
                        horas, minutos = partes
                        return f"{signo}{int(horas):02d}:{int(minutos):02d}:00"
                    else:
                        # Unknown format, return default
                        return "00:00:00"
                
                resultado = {
                    "employee": str(row.get("employee", "")),
                    "Nombre": str(row.get("Nombre", "Sin nombre")),
                    "total_horas_trabajadas": formatear_tiempo(safe_time_value(row.get("total_horas_trabajadas"))),
                    "total_horas_esperadas": formatear_tiempo(safe_time_value(row.get("total_horas_esperadas"))),
                    "total_horas_descontadas_permiso": formatear_tiempo(safe_time_value(row.get("total_horas_descontadas_permiso"))),
                    "total_horas_descanso": formatear_tiempo(safe_time_value(row.get("total_horas_descanso"))),
                    "total_horas": formatear_tiempo(safe_time_value(row.get("total_horas"))),
                    "total_retardos": str(safe_int_value(row.get("total_retardos"))),
                    "faltas_del_periodo": str(safe_int_value(row.get("faltas_del_periodo"))),
                    "faltas_justificadas": str(safe_int_value(row.get("faltas_justificadas"))),
                    "total_faltas": str(safe_int_value(row.get("total_faltas"))),
                    "episodios_ausencia": str(safe_int_value(row.get("episodios_ausencia", 0))),
                    "total_salidas_anticipadas": str(safe_int_value(row.get("total_salidas_anticipadas", 0))),
                    "diferencia_HHMMSS": formatear_tiempo(safe_time_value(row.get("diferencia_HHMMSS"))),
                }
                resultados.append(resultado)
                
            except Exception as e:
                print(f"⚠️ Error formateando fila {index}: {e}")
                continue

        return resultados


# Función de conveniencia para usar desde las views
def generar_reporte_completo(start_date: str, end_date: str, sucursal: str, device_filter: str) -> dict:
    """
    Función de conveniencia para generar reportes desde las views de Django.
    
    Args:
        start_date: Fecha de inicio (YYYY-MM-DD)
        end_date: Fecha de fin (YYYY-MM-DD)
        sucursal: Nombre de la sucursal
        device_filter: Filtro de dispositivo para la API
        
    Returns:
        Dict con los resultados del reporte
    """
    manager = AttendanceReportManager()
    return manager.generate_attendance_report(start_date, end_date, sucursal, device_filter)


if __name__ == "__main__":
    """
    Para uso standalone (testing)
    """
    # Configuración para testing
    config = {
        "start_date": "2025-01-01",
        "end_date": "2025-01-15", 
        "sucursal": "Villas",
        "device_filter": "%Villas%"
    }
    
    manager = AttendanceReportManager()
    result = manager.generate_attendance_report(**config)
    
    if result["success"]:
        print("\n" + "="*60)
        print("🎉 REPORTE GENERADO EXITOSAMENTE")
        print("="*60)
        for key, value in result["metadata"].items():
            print(f"📊 {key.replace('_', ' ').title()}: {value}")
        print(f"\n📋 Total empleados procesados: {len(result['data'])}")
    else:
        print("\n" + "="*60)
        print("❌ FALLÓ LA GENERACIÓN DEL REPORTE")
        print("="*60)
        print(f"Error: {result.get('error', 'Error desconocido')}")