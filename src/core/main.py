from datetime import datetime
from typing import List, Dict
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np # Asegúrate de que numpy esté importado aquí
from .utils import td_to_str # Asegúrate de que td_to_str esté importado

from .api_client import APIClient, procesar_permisos_empleados
# Se importan la clase y las nuevas funciones de services
from .services import AttendanceProcessor, calcular_metricas_adicionales, agregar_datos_dashboard_por_sucursal
from .models import Empleado
# Asegúrate que estén importadas
from .services import calcular_metricas_adicionales, agregar_datos_dashboard_por_sucursal

class AttendanceReportManager:
    """Clase de ayuda para obtener datos, ya no genera el reporte directamente."""

    def __init__(self):
        """ ✅ CORREGIDO: Constructor usa doble guion bajo _init_ """
        self.api_client = APIClient()

    def _prepare_report_data(self, start_date: str, end_date: str, sucursal: str):
        """Método unificado para obtener datos base para cualquier reporte."""
        load_dotenv()
        if not all([os.getenv("ASIATECH_API_KEY"), os.getenv("ASIATECH_API_SECRET")]):
            raise ValueError("Credenciales de API no configuradas")

        if sucursal != 'Todas':
            """ ✅ CORREGIDO: Filtro de Django usa doble guion bajo __ """
            empleados = Empleado.objects.filter(
                asignaciones__sucursal__nombre_sucursal=sucursal).distinct()
        else:
            empleados = Empleado.objects.all()

        codigos_empleados = [str(
            emp.codigo_frappe) for emp in empleados if emp.codigo_frappe is not None]

        # Este Mapeo ahora está en api_client.py, solo pasamos el filtro
        device_map = {"Villas": "Villas", "31pte": "31pte",
                      "Nave": "Nave", "RioBlanco": "RioBlanco", "Todas": "Todas"}
        device_filter_key = device_map.get(sucursal, "Todas")


        checkin_records = self.api_client.fetch_checkins(
            start_date, end_date, device_filter_key) # Pasamos la clave, no el patrón
        leave_records = self.api_client.fetch_leave_applications(
            start_date, end_date)
        permisos_dict = procesar_permisos_empleados(leave_records)

        return codigos_empleados, checkin_records, permisos_dict

# =================================================================
# === FUNCIONES QUE FALTABAN (RE-AGREGADAS) ===
# =================================================================

def generar_reporte_completo(start_date: str, end_date: str, sucursal: str) -> dict:
    """Orquestador para el Reporte de Horas (Resumen)."""
    try:
        manager = AttendanceReportManager()
        processor = AttendanceProcessor()

        codigos, checkins, permisos = manager._prepare_report_data(
            start_date, end_date, sucursal)
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

        codigos, checkins, permisos = manager._prepare_report_data(
            start_date, end_date, sucursal)
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

def generar_datos_dashboard_general(start_date: str, end_date: str) -> dict:
    empty_summary = {"total_attendances": 0, "total_permissions": 0,
                     "total_absences": 0, "total_justified_absences": 0}
    empty_data = {"branches": [], "period_summary": empty_summary,
                  "employee_summary_kpis": [], "employee_performance_kpis": []}

    try:
        manager = AttendanceReportManager()
        processor = AttendanceProcessor()

        # 1. Obtener datos
        codigos, checkins, permisos = manager._prepare_report_data(
            start_date, end_date, sucursal='Todas')
        if not codigos:
            return {"success": True, "data": empty_data}

        # 2. Procesar reportes
        df_detalle, df_resumen = processor.procesar_reporte_completo(
            checkin_data=checkins, permisos_dict=permisos, start_date=start_date,
            end_date=end_date, employee_codes=codigos
        )
        if df_resumen.empty or df_detalle.empty:
            return {"success": True, "data": empty_data}

        # =========================================================
        # 🔥🔥🔥 BLOQUE NUEVO: FILTRADO DE EMPLEADOS ACTIVOS 🔥🔥🔥
        # =========================================================
        # Esto elimina a los "borrados" (Elvis) de TODO el dashboard (totales y listas)
        try:
            from core.models import Empleado
            
            # Recolectamos todos los IDs que vienen de los relojes checadores
            ids_raw = pd.concat([df_resumen['employee'], df_detalle['employee']]).unique()
            ids_ints = []
            for x in ids_raw:
                try: ids_ints.append(int(float(x)))
                except: pass
            
            # 🔥 CAMBIO CLAVE 1: Usamos .objects (no all_objects) y forzamos is_active=True
            # Esto asegura que SOLO traiga a los que existen en Admin como activos.
            empleados_activos = Empleado.objects.filter(empleado_id__in=ids_ints, is_active=True)
            
            # Creamos un set de IDs válidos (convertidos a string para comparar con el DataFrame)
            ids_validos_str = set(str(emp.empleado_id) for emp in empleados_activos)
            
            # Función auxiliar para normalizar el ID del DF y ver si está en la lista de activos
            def es_activo(valor_id):
                try: 
                    val_str = str(int(float(valor_id)))
                    return val_str in ids_validos_str
                except: 
                    return False

            # 🔥 CAMBIO CLAVE 2: Recortamos los DataFrames. Si no es activo, se va.
            df_resumen = df_resumen[df_resumen['employee'].apply(es_activo)]
            df_detalle = df_detalle[df_detalle['employee'].apply(es_activo)]
            
            # Si después de filtrar no queda nadie, retornamos vacío
            if df_resumen.empty or df_detalle.empty:
                return {"success": True, "data": empty_data}

        except Exception as e:
            # Si falla el filtrado (ej. error de DB), imprimimos pero continuamos con lo que haya
            print(f"Advertencia al filtrar activos: {e}")
        # =========================================================


        # 3. Métricas y Agregados (Ahora ya limpios sin el empleado borrado)
        df_metricas = calcular_metricas_adicionales(df_resumen.copy(), df_detalle.copy())
        datos_agregados = agregar_datos_dashboard_por_sucursal(df_metricas.copy())

        # 4. Resumen del periodo
        total_attendances = int(df_detalle[(df_detalle['horas_esperadas'].dt.total_seconds() > 0) & (
            df_detalle['checados_count'] > 0) & (df_detalle['tiene_permiso'] == False)].shape[0])
        total_permissions = int(df_detalle['tiene_permiso'].sum())
        total_unjustified_absences = int(df_resumen['faltas_del_periodo'].sum()) if 'faltas_del_periodo' in df_resumen.columns else 0
        total_justified_absences = int(df_resumen['faltas_justificadas'].sum()) if 'faltas_justificadas' in df_resumen.columns else 0
        
        period_summary = {
            "total_attendances": total_attendances,
            "total_permissions": total_permissions,
            "total_absences": total_unjustified_absences + total_justified_absences,
            "total_justified_absences": total_justified_absences
        }

        # ---------------------------------------------------------
        # 5. PREPARACIÓN DE TABLA "RESUMEN HORAS"
        # ---------------------------------------------------------
        df_summary_kpis_agg = df_resumen.groupby('employee').agg(
            Nombre=('Nombre', 'first'),
            total_horas_trabajadas_td=('total_horas_trabajadas_td', 'sum'),
            total_horas_esperadas_td=('total_horas_esperadas_td', 'sum'), 
            total_horas_td=('total_horas_td', 'sum'), 
            total_retardos=('total_retardos', 'sum'),
            faltas_del_periodo=('faltas_del_periodo', 'sum')
        ).reset_index()

        df_summary_kpis_agg['diferencia_td'] = df_summary_kpis_agg['total_horas_trabajadas_td'] - df_summary_kpis_agg['total_horas_td']
        
        df_summary_kpis_agg['total_horas_trabajadas'] = df_summary_kpis_agg['total_horas_trabajadas_td'].apply(td_to_str)
        df_summary_kpis_agg['total_horas_esperadas'] = df_summary_kpis_agg['total_horas_esperadas_td'].apply(td_to_str)
        df_summary_kpis_agg['diferencia_HHMMSS'] = df_summary_kpis_agg['diferencia_td'].apply(lambda x: f"-{td_to_str(abs(x))}" if x.total_seconds() < 0 else td_to_str(x))
        
        df_summary_kpis = df_summary_kpis_agg.copy() 

        summary_rename_map = {
            'employee': 'ID',
            'Nombre': 'Empleado',
            'total_horas_trabajadas': 'Hrs. Trabajadas',
            'total_horas_esperadas': 'Hrs. Planificadas',
            'diferencia_HHMMSS': 'Variación',
            'total_retardos': 'Retardos',
            'faltas_del_periodo': 'Ausencias'
        }
        df_summary_kpis = df_summary_kpis.rename(columns=summary_rename_map)

        # =========================================================
        # CARGA Y MAPEO DE NOMBRES COMPLETOS (SECCIÓN ORIGINAL REUTILIZADA)
        # =========================================================
        mapa_nombres = {}
        try:
            ids_ints = []
            ids_raw = list(df_summary_kpis['ID'].unique())
            for x in ids_raw:
                try: ids_ints.append(int(float(x)))
                except: pass
            
            # Reutilizamos el filtro correcto: objects + is_active
            empleados_db = Empleado.objects.filter(empleado_id__in=ids_ints, is_active=True)
            
            mapa_nombres = {
                str(emp.empleado_id): f"{emp.nombre} {emp.apellido_paterno} {emp.apellido_materno or ''}".strip()
                for emp in empleados_db
            }
        except Exception:
            pass

        # FUNCIÓN DE INYECCIÓN
        def aplicar_nombres_robusto(df_target):
            def normalizar_id(valor):
                try: return str(int(float(valor)))
                except: return str(valor).strip()

            ids_limpios = df_target['ID'].apply(normalizar_id)
            nombres_series = ids_limpios.map(mapa_nombres)
            
            if 'Empleado' in df_target.columns:
                 nombres_series = nombres_series.fillna(df_target['Empleado']).fillna("Sin Nombre")
            elif 'Nombre' in df_target.columns:
                 nombres_series = nombres_series.fillna(df_target['Nombre']).fillna("Sin Nombre")
            else:
                 nombres_series = nombres_series.fillna("Sin Nombre")
            
            df_target['Empleado'] = nombres_series 
            df_target['Nombre'] = nombres_series   
            df_target['nombre'] = nombres_series   
            df_target['empleado'] = nombres_series 
            df_target['employee'] = nombres_series 
            return df_target

        # APLICAMOS A TABLA 1 (RESUMEN)
        df_summary_kpis = aplicar_nombres_robusto(df_summary_kpis)
        
        cols_seguras = ['ID', 'employee', 'Empleado', 'Nombre', 'Hrs. Trabajadas', 'Hrs. Planificadas', 'Variación', 'Retardos', 'Ausencias']
        df_summary_kpis = df_summary_kpis[list(set(cols_seguras).intersection(df_summary_kpis.columns))]
        summary_kpis_list = df_summary_kpis.to_dict('records')

        # ---------------------------------------------------------
        # 6. PREPARACIÓN DE TABLA "KPIs RENDIMIENTO"
        # ---------------------------------------------------------
        dias_laborables_total = df_detalle[df_detalle['horas_esperadas'].dt.total_seconds() > 0].groupby('employee').size()
        dias_laborables_total.name = 'dias_laborables_total'

        df_perf_agg = df_resumen.groupby('employee').agg(
            Nombre=('Nombre', 'first'),
            Faltas=('faltas_del_periodo', 'sum'),
            Retardos=('total_retardos', 'sum'),
            Salidas=('total_salidas_anticipadas', 'sum'),
            Faltas_Justificadas=('faltas_justificadas', 'sum')
        ).reset_index()
        
        df_perf_agg = df_perf_agg.merge(df_summary_kpis_agg[['employee', 'total_horas_trabajadas_td', 'total_horas_td']], on='employee', how='left')
        df_perf_agg['employee'] = df_perf_agg['employee'].astype(str)
        dias_laborables_total.index = dias_laborables_total.index.astype(str)
        df_perf_agg = df_perf_agg.merge(dias_laborables_total, on='employee', how='left').fillna(0)

        # Cálculos de porcentajes
        mask_dlp_total = df_perf_agg['dias_laborables_total'] > 0
        total_horas_trabajadas_s = df_perf_agg['total_horas_trabajadas_td'].dt.total_seconds()
        total_horas_netas_s = df_perf_agg['total_horas_td'].dt.total_seconds()
        
        df_perf_agg['Eficiencia Horas (%)'] = 100.0
        mask_hnp_total = total_horas_netas_s > 0
        if mask_hnp_total.any():
            df_perf_agg.loc[mask_hnp_total, 'Eficiencia Horas (%)'] = (total_horas_trabajadas_s[mask_hnp_total] / total_horas_netas_s[mask_hnp_total]) * 100

        df_perf_agg['Índice Puntualidad (%)'] = 100.0
        if mask_dlp_total.any():
            denom = df_perf_agg.loc[mask_dlp_total, 'dias_laborables_total']
            numer = denom - df_perf_agg.loc[mask_dlp_total, 'Retardos']
            df_perf_agg.loc[mask_dlp_total, 'Índice Puntualidad (%)'] = (numer.clip(lower=0) / denom) * 100

        df_perf_agg['SIC'] = 100.0
        if mask_dlp_total.any():
            denom = df_perf_agg.loc[mask_dlp_total, 'dias_laborables_total']
            numer = denom - (df_perf_agg.loc[mask_dlp_total, 'Faltas'] + df_perf_agg.loc[mask_dlp_total, 'Retardos'] + df_perf_agg.loc[mask_dlp_total, 'Salidas'])
            df_perf_agg.loc[mask_dlp_total, 'SIC'] = (numer.clip(lower=0) / denom) * 100

        df_perf_agg['Tasa Ausentismo (%)'] = 0.0
        if mask_dlp_total.any():
            denom = df_perf_agg.loc[mask_dlp_total, 'dias_laborables_total']
            numer = df_perf_agg.loc[mask_dlp_total, 'Faltas']
            df_perf_agg.loc[mask_dlp_total, 'Tasa Ausentismo (%)'] = (numer / denom) * 100

        df_performance_kpis = df_perf_agg.rename(columns={'employee': 'ID', 'Faltas_Justificadas': 'Faltas Justificadas'})

        # APLICAMOS A TABLA 2
        df_performance_kpis = aplicar_nombres_robusto(df_performance_kpis)

        cols_kpis = ['ID', 'Nombre', 'Empleado', 'employee', 'Faltas Justificadas', 'Tasa Ausentismo (%)', 'Índice Puntualidad (%)', 'Eficiencia Horas (%)', 'SIC']
        df_performance_kpis = df_performance_kpis[list(set(cols_kpis).intersection(df_performance_kpis.columns))]
        
        performance_kpis_list = df_performance_kpis.round(1).to_dict('records')

        final_data = {
            "branches": datos_agregados,
            "period_summary": period_summary,
            "employee_summary_kpis": summary_kpis_list,
            "employee_performance_kpis": performance_kpis_list
        }
        
        return {"success": True, "data": final_data}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": f"Error interno: {str(e)}", "data": empty_data}

        # FUNCIÓN DE INYECCIÓN
        def aplicar_nombres_robusto(df_target):
            # Normalizador que coincide EXACTAMENTE con la llave generada arriba
            def normalizar_id(valor):
                try: return str(int(float(valor)))
                except: return str(valor).strip()

            ids_limpios = df_target['ID'].apply(normalizar_id)
            nombres_series = ids_limpios.map(mapa_nombres)
            
            # Fallback: Si no hay match en el mapa, usa el nombre original (incompleto)
            if 'Empleado' in df_target.columns:
                 nombres_series = nombres_series.fillna(df_target['Empleado']).fillna("Sin Nombre")
            elif 'Nombre' in df_target.columns:
                 nombres_series = nombres_series.fillna(df_target['Nombre']).fillna("Sin Nombre")
            else:
                 nombres_series = nombres_series.fillna("Sin Nombre")
            
            df_target['Empleado'] = nombres_series 
            df_target['Nombre'] = nombres_series   
            # Actualizamos también las columnas de ID/employee para mantener consistencia visual si fuera necesario
            return df_target

        # APLICAMOS A TABLA 1 (RESUMEN)
        df_summary_kpis = aplicar_nombres_robusto(df_summary_kpis)
        
        cols_seguras = ['ID', 'employee', 'Empleado', 'Nombre', 'Hrs. Trabajadas', 'Hrs. Planificadas', 'Variación', 'Retardos', 'Ausencias']
        df_summary_kpis = df_summary_kpis[list(set(cols_seguras).intersection(df_summary_kpis.columns))]
        summary_kpis_list = df_summary_kpis.to_dict('records')

        # ---------------------------------------------------------
        # 6. PREPARACIÓN DE TABLA "KPIs RENDIMIENTO"
        # ---------------------------------------------------------
        dias_laborables_total = df_detalle[df_detalle['horas_esperadas'].dt.total_seconds() > 0].groupby('employee').size()
        dias_laborables_total.name = 'dias_laborables_total'

        df_perf_agg = df_resumen.groupby('employee').agg(
            Nombre=('Nombre', 'first'),
            Faltas=('faltas_del_periodo', 'sum'),
            Retardos=('total_retardos', 'sum'),
            Salidas=('total_salidas_anticipadas', 'sum'),
            Faltas_Justificadas=('faltas_justificadas', 'sum')
        ).reset_index()
        
        df_perf_agg = df_perf_agg.merge(df_summary_kpis_agg[['employee', 'total_horas_trabajadas_td', 'total_horas_td']], on='employee', how='left')
        df_perf_agg['employee'] = df_perf_agg['employee'].astype(str)
        dias_laborables_total.index = dias_laborables_total.index.astype(str)
        df_perf_agg = df_perf_agg.merge(dias_laborables_total, on='employee', how='left').fillna(0)

        # Cálculos de porcentajes
        mask_dlp_total = df_perf_agg['dias_laborables_total'] > 0
        total_horas_trabajadas_s = df_perf_agg['total_horas_trabajadas_td'].dt.total_seconds()
        total_horas_netas_s = df_perf_agg['total_horas_td'].dt.total_seconds()
        
        df_perf_agg['Eficiencia Horas (%)'] = 100.0
        mask_hnp_total = total_horas_netas_s > 0
        if mask_hnp_total.any():
            df_perf_agg.loc[mask_hnp_total, 'Eficiencia Horas (%)'] = (total_horas_trabajadas_s[mask_hnp_total] / total_horas_netas_s[mask_hnp_total]) * 100

        df_perf_agg['Índice Puntualidad (%)'] = 100.0
        if mask_dlp_total.any():
            denom = df_perf_agg.loc[mask_dlp_total, 'dias_laborables_total']
            numer = denom - df_perf_agg.loc[mask_dlp_total, 'Retardos']
            df_perf_agg.loc[mask_dlp_total, 'Índice Puntualidad (%)'] = (numer.clip(lower=0) / denom) * 100

        df_perf_agg['SIC'] = 100.0
        if mask_dlp_total.any():
            denom = df_perf_agg.loc[mask_dlp_total, 'dias_laborables_total']
            numer = denom - (df_perf_agg.loc[mask_dlp_total, 'Faltas'] + df_perf_agg.loc[mask_dlp_total, 'Retardos'] + df_perf_agg.loc[mask_dlp_total, 'Salidas'])
            df_perf_agg.loc[mask_dlp_total, 'SIC'] = (numer.clip(lower=0) / denom) * 100

        df_perf_agg['Tasa Ausentismo (%)'] = 0.0
        if mask_dlp_total.any():
            denom = df_perf_agg.loc[mask_dlp_total, 'dias_laborables_total']
            numer = df_perf_agg.loc[mask_dlp_total, 'Faltas']
            df_perf_agg.loc[mask_dlp_total, 'Tasa Ausentismo (%)'] = (numer / denom) * 100

        df_performance_kpis = df_perf_agg.rename(columns={'employee': 'ID', 'Faltas_Justificadas': 'Faltas Justificadas'})

        # APLICAMOS A TABLA 2
        df_performance_kpis = aplicar_nombres_robusto(df_performance_kpis)

        cols_kpis = ['ID', 'Nombre', 'Empleado', 'employee', 'Faltas Justificadas', 'Tasa Ausentismo (%)', 'Índice Puntualidad (%)', 'Eficiencia Horas (%)', 'SIC']
        df_performance_kpis = df_performance_kpis[list(set(cols_kpis).intersection(df_performance_kpis.columns))]
        
        performance_kpis_list = df_performance_kpis.round(1).to_dict('records')

        final_data = {
            "branches": datos_agregados,
            "period_summary": period_summary,
            "employee_summary_kpis": summary_kpis_list,
            "employee_performance_kpis": performance_kpis_list
        }
        
        return {"success": True, "data": final_data}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": f"Error interno: {str(e)}", "data": empty_data}

#31pte
def generar_datos_dashboard_31pte(start_date: str, end_date: str) -> dict:
    empty_summary = {"total_attendances": 0, "total_permissions": 0,
                     "total_absences": 0, "total_justified_absences": 0}
    empty_data = {"branches": [], "period_summary": empty_summary,
                  "employee_summary_kpis": [], "employee_performance_kpis": []}

    try:
        manager = AttendanceReportManager()
        processor = AttendanceProcessor()

        print(f"[INFO Dashboard 31pte] Obteniendo datos {start_date} a {end_date}")
        codigos, checkins, permisos = manager._prepare_report_data(
            start_date, end_date, sucursal='31pte')
        if not codigos:
            return {"success": True, "data": empty_data}

        print("[INFO Dashboard 31pte] Procesando reporte completo...")
        df_detalle, df_resumen = processor.procesar_reporte_completo(
            checkin_data=checkins, permisos_dict=permisos, start_date=start_date,
            end_date=end_date, employee_codes=codigos
        )
        if df_resumen.empty or df_detalle.empty:
            return {"success": True, "data": empty_data}

        print("[INFO Dashboard 31pte] Calculando métricas adicionales...")
        df_metricas = calcular_metricas_adicionales(
            df_resumen.copy(), df_detalle.copy())

        print("[INFO Dashboard 31pte] Agregando datos por sucursal...")
        datos_agregados = agregar_datos_dashboard_por_sucursal(
            df_metricas.copy())

        print("[INFO Dashboard 31pte] Calculando resumen del periodo...")
        total_attendances = int(df_detalle[(df_detalle['horas_esperadas'].dt.total_seconds() > 0) & (
            df_detalle['checados_count'] > 0) & (df_detalle['tiene_permiso'] == False)].shape[0])
        total_permissions = int(df_detalle['tiene_permiso'].sum())
        
        total_unjustified_absences = int(df_resumen['faltas_del_periodo'].sum(
        )) if 'faltas_del_periodo' in df_resumen.columns else 0
        total_justified_absences = int(df_resumen['faltas_justificadas'].sum(
        )) if 'faltas_justificadas' in df_resumen.columns else 0
        total_absences_kpi = total_unjustified_absences + total_justified_absences

        period_summary = {
            "total_attendances": total_attendances,
            "total_permissions": total_permissions,
            "total_absences": total_absences_kpi,
            "total_justified_absences": total_justified_absences
        }
        print(f"[INFO Dashboard 31pte] Resumen Periodo: {period_summary}")

        print("[INFO Dashboard 31pte] Preparando Resumen Horas por Empleado...")
        df_summary_kpis_agg = df_resumen.groupby('employee').agg(
            Nombre=('Nombre', 'first'),
            total_horas_trabajadas_td=('total_horas_trabajadas_td', 'sum'),
            total_horas_esperadas_td=('total_horas_esperadas_td', 'sum'), # <-- CORREGIDO
            total_horas_td=('total_horas_td', 'sum'), # <-- CORREGIDO
            total_retardos=('total_retardos', 'sum'),
            faltas_del_periodo=('faltas_del_periodo', 'sum')
        ).reset_index()
        
        df_summary_kpis_agg['diferencia_td'] = df_summary_kpis_agg['total_horas_trabajadas_td'] - df_summary_kpis_agg['total_horas_td']
        df_summary_kpis_agg['total_horas_trabajadas'] = df_summary_kpis_agg['total_horas_trabajadas_td'].apply(td_to_str)
        df_summary_kpis_agg['total_horas_esperadas'] = df_summary_kpis_agg['total_horas_esperadas_td'].apply(td_to_str)
        df_summary_kpis_agg['diferencia_HHMMSS'] = df_summary_kpis_agg['diferencia_td'].apply(lambda x: f"-{td_to_str(abs(x))}" if x.total_seconds() < 0 else td_to_str(x))
        df_summary_kpis = df_summary_kpis_agg.copy()
        
        summary_rename_map = {
            'employee': 'ID', 'Nombre': 'Empleado', 'total_horas_trabajadas': 'Hrs. Trabajadas',
            'total_horas_esperadas': 'Hrs. Planificadas', 'diferencia_HHMMSS': 'Variación',
            'total_retardos': 'Retardos', 'faltas_del_periodo': 'Ausencias'
        }
        final_summary_cols = ['ID', 'Empleado', 'Hrs. Trabajadas',
                              'Hrs. Planificadas', 'Variación', 'Retardos', 'Ausencias']
        df_summary_kpis = df_summary_kpis.rename(columns=summary_rename_map)
        df_summary_kpis = df_summary_kpis[list(
            set(final_summary_cols).intersection(df_summary_kpis.columns))]
        summary_kpis_list = df_summary_kpis.to_dict('records')

        print("[INFO Dashboard 31pte] Preparando KPIs de Rendimiento por Empleado...")
        dias_laborables_total = df_detalle[df_detalle['horas_esperadas'].dt.total_seconds() > 0].groupby('employee').size()
        dias_laborables_total.name = 'dias_laborables_total'
        df_perf_agg = df_resumen.groupby('employee').agg(
            Nombre=('Nombre', 'first'), Faltas=('faltas_del_periodo', 'sum'),
            Retardos=('total_retardos', 'sum'), Salidas=('total_salidas_anticipadas', 'sum'),
            Faltas_Justificadas=('faltas_justificadas', 'sum')
        ).reset_index()
        df_perf_agg = df_perf_agg.merge(
            df_summary_kpis_agg[['employee', 'total_horas_trabajadas_td', 'total_horas_td']], on='employee', how='left')
        
        df_perf_agg['employee'] = df_perf_agg['employee'].astype(str)
        dias_laborables_total.index = dias_laborables_total.index.astype(str)
        df_perf_agg = df_perf_agg.merge(dias_laborables_total, on='employee', how='left').fillna(0)

        mask_dlp_total = df_perf_agg['dias_laborables_total'] > 0
        
        total_horas_trabajadas_s = df_perf_agg['total_horas_trabajadas_td'].dt.total_seconds()
        total_horas_netas_s = df_perf_agg['total_horas_td'].dt.total_seconds()
        df_perf_agg['Eficiencia Horas (%)'] = 100.0
        mask_hnp_total = total_horas_netas_s > 0
        if mask_hnp_total.any():
            df_perf_agg.loc[mask_hnp_total, 'Eficiencia Horas (%)'] = np.divide(
                total_horas_trabajadas_s[mask_hnp_total], total_horas_netas_s[mask_hnp_total],
                out=np.full_like(total_horas_trabajadas_s[mask_hnp_total], 100.0), where=total_horas_netas_s[mask_hnp_total]!=0
            ) * 100
        
        df_perf_agg['Índice Puntualidad (%)'] = 100.0
        if mask_dlp_total.any():
            denom = df_perf_agg.loc[mask_dlp_total, 'dias_laborables_total'].astype(float)
            numer = denom - df_perf_agg.loc[mask_dlp_total, 'Retardos'].astype(float)
            df_perf_agg.loc[mask_dlp_total, 'Índice Puntualidad (%)'] = np.divide(numer.clip(lower=0), denom, out=np.full_like(numer, 100.0), where=denom!=0) * 100
        
        df_perf_agg['SIC'] = 100.0
        if mask_dlp_total.any():
            denom = df_perf_agg.loc[mask_dlp_total, 'dias_laborables_total'].astype(float)
            numer = denom - (df_perf_agg.loc[mask_dlp_total, 'Faltas'] + df_perf_agg.loc[mask_dlp_total, 'Retardos'] + df_perf_agg.loc[mask_dlp_total, 'Salidas'])
            df_perf_agg.loc[mask_dlp_total, 'SIC'] = np.divide(numer.clip(lower=0), denom, out=np.full_like(numer, 100.0), where=denom!=0) * 100

        df_perf_agg['Tasa Ausentismo (%)'] = 0.0
        if mask_dlp_total.any():
            denom = df_perf_agg.loc[mask_dlp_total, 'dias_laborables_total'].astype(float)
            numer = df_perf_agg.loc[mask_dlp_total, 'Faltas'].astype(float)
            df_perf_agg.loc[mask_dlp_total, 'Tasa Ausentismo (%)'] = np.divide(numer, denom, out=np.zeros_like(numer), where=denom!=0) * 100
        
        df_performance_kpis = df_perf_agg.rename(columns={'employee': 'ID', 'Faltas_Justificadas': 'Faltas Justificadas'})
        perf_cols_needed = ['ID', 'Nombre', 'Faltas Justificadas', 'Tasa Ausentismo (%)', 'Índice Puntualidad (%)', 'Eficiencia Horas (%)', 'SIC']
        for col in perf_cols_needed:
            if col not in df_performance_kpis.columns: df_performance_kpis[col] = 0
        df_performance_kpis = df_performance_kpis[perf_cols_needed]
        performance_kpis_list = df_performance_kpis.round(1).to_dict('records')

        final_data = {
            "branches": datos_agregados,
            "period_summary": period_summary,
            "employee_summary_kpis": summary_kpis_list,
            "employee_performance_kpis": performance_kpis_list
        }
        print("[INFO Dashboard 31pte] Datos finales listos para enviar.")
        return {"success": True, "data": final_data}

    except Exception as e:
        import traceback
        print(f"[ERROR Dashboard 31pte]: Ocurrió una excepción - {e}")
        traceback.print_exc()
        return {"success": False, "error": f"Error interno: {str(e)}", "data": empty_data}

#Villas
def generar_datos_dashboard_villas(start_date: str, end_date: str) -> dict:
    empty_summary = {"total_attendances": 0, "total_permissions": 0,
                     "total_absences": 0, "total_justified_absences": 0}
    empty_data = {"branches": [], "period_summary": empty_summary,
                  "employee_summary_kpis": [], "employee_performance_kpis": []}

    try:
        manager = AttendanceReportManager()
        processor = AttendanceProcessor()

        print(f"[INFO Dashboard Villas] Obteniendo datos {start_date} a {end_date}")
        codigos, checkins, permisos = manager._prepare_report_data(
            start_date, end_date, sucursal='Villas')
        if not codigos:
            return {"success": True, "data": empty_data}

        print("[INFO Dashboard Villas] Procesando reporte completo...")
        df_detalle, df_resumen = processor.procesar_reporte_completo(
            checkin_data=checkins, permisos_dict=permisos, start_date=start_date,
            end_date=end_date, employee_codes=codigos
        )
        if df_resumen.empty or df_detalle.empty:
            return {"success": True, "data": empty_data}

        print("[INFO Dashboard Villas] Calculando métricas adicionales...")
        df_metricas = calcular_metricas_adicionales(
            df_resumen.copy(), df_detalle.copy())

        print("[INFO Dashboard Villas] Agregando datos por sucursal...")
        datos_agregados = agregar_datos_dashboard_por_sucursal(
            df_metricas.copy())

        print("[INFO Dashboard Villas] Calculando resumen del periodo...")
        total_attendances = int(df_detalle[(df_detalle['horas_esperadas'].dt.total_seconds() > 0) & (
            df_detalle['checados_count'] > 0) & (df_detalle['tiene_permiso'] == False)].shape[0])
        total_permissions = int(df_detalle['tiene_permiso'].sum())
        
        total_unjustified_absences = int(df_resumen['faltas_del_periodo'].sum(
        )) if 'faltas_del_periodo' in df_resumen.columns else 0
        total_justified_absences = int(df_resumen['faltas_justificadas'].sum(
        )) if 'faltas_justificadas' in df_resumen.columns else 0
        total_absences_kpi = total_unjustified_absences + total_justified_absences

        period_summary = {
            "total_attendances": total_attendances,
            "total_permissions": total_permissions,
            "total_absences": total_absences_kpi,
            "total_justified_absences": total_justified_absences
        }
        print(f"[INFO Dashboard Villas] Resumen Periodo: {period_summary}")

        print("[INFO Dashboard Villas] Preparando Resumen Horas por Empleado...")
        
        # --- INICIA CORRECCIÓN DEL ERROR 'str' object ---
        df_summary_kpis_agg = df_resumen.groupby('employee').agg(
            Nombre=('Nombre', 'first'),
            total_horas_trabajadas_td=('total_horas_trabajadas_td', 'sum'),
            total_horas_esperadas_td=('total_horas_esperadas_td', 'sum'), # <-- CORREGIDO
            total_horas_td=('total_horas_td', 'sum'), # <-- CORREGIDO
            total_retardos=('total_retardos', 'sum'),
            faltas_del_periodo=('faltas_del_periodo', 'sum')
        ).reset_index()
        # --- FIN CORRECCIÓN DEL ERROR 'str' object ---
        
        df_summary_kpis_agg['diferencia_td'] = df_summary_kpis_agg['total_horas_trabajadas_td'] - df_summary_kpis_agg['total_horas_td']
        df_summary_kpis_agg['total_horas_trabajadas'] = df_summary_kpis_agg['total_horas_trabajadas_td'].apply(td_to_str)
        df_summary_kpis_agg['total_horas_esperadas'] = df_summary_kpis_agg['total_horas_esperadas_td'].apply(td_to_str)
        df_summary_kpis_agg['diferencia_HHMMSS'] = df_summary_kpis_agg['diferencia_td'].apply(lambda x: f"-{td_to_str(abs(x))}" if x.total_seconds() < 0 else td_to_str(x))
        df_summary_kpis = df_summary_kpis_agg.copy()
        summary_rename_map = {
            'employee': 'ID', 'Nombre': 'Empleado', 'total_horas_trabajadas': 'Hrs. Trabajadas',
            'total_horas_esperadas': 'Hrs. Planificadas', 'diferencia_HHMMSS': 'Variación',
            'total_retardos': 'Retardos', 'faltas_del_periodo': 'Ausencias'
        }
        final_summary_cols = ['ID', 'Empleado', 'Hrs. Trabajadas',
                              'Hrs. Planificadas', 'Variación', 'Retardos', 'Ausencias']
        df_summary_kpis = df_summary_kpis.rename(columns=summary_rename_map)
        df_summary_kpis = df_summary_kpis[list(
            set(final_summary_cols).intersection(df_summary_kpis.columns))]
        summary_kpis_list = df_summary_kpis.to_dict('records')


        print("[INFO Dashboard Villas] Preparando KPIs de Rendimiento por Empleado...")
        dias_laborables_total = df_detalle[df_detalle['horas_esperadas'].dt.total_seconds() > 0].groupby('employee').size()
        dias_laborables_total.name = 'dias_laborables_total'
        df_perf_agg = df_resumen.groupby('employee').agg(
            Nombre=('Nombre', 'first'), Faltas=('faltas_del_periodo', 'sum'),
            Retardos=('total_retardos', 'sum'), Salidas=('total_salidas_anticipadas', 'sum'),
            Faltas_Justificadas=('faltas_justificadas', 'sum')
        ).reset_index()
        df_perf_agg = df_perf_agg.merge(
            df_summary_kpis_agg[['employee', 'total_horas_trabajadas_td', 'total_horas_td']], on='employee', how='left')
        
        df_perf_agg['employee'] = df_perf_agg['employee'].astype(str)
        dias_laborables_total.index = dias_laborables_total.index.astype(str)
        df_perf_agg = df_perf_agg.merge(dias_laborables_total, on='employee', how='left').fillna(0)
        
        mask_dlp_total = df_perf_agg['dias_laborables_total'] > 0
        total_horas_trabajadas_s = df_perf_agg['total_horas_trabajadas_td'].dt.total_seconds()
        total_horas_netas_s = df_perf_agg['total_horas_td'].dt.total_seconds()
        df_perf_agg['Eficiencia Horas (%)'] = 100.0
        mask_hnp_total = total_horas_netas_s > 0
        if mask_hnp_total.any():
            df_perf_agg.loc[mask_hnp_total, 'Eficiencia Horas (%)'] = np.divide(
                total_horas_trabajadas_s[mask_hnp_total], total_horas_netas_s[mask_hnp_total],
                out=np.full_like(total_horas_trabajadas_s[mask_hnp_total], 100.0), where=total_horas_netas_s[mask_hnp_total]!=0
            ) * 100
        df_perf_agg['Índice Puntualidad (%)'] = 100.0
        if mask_dlp_total.any():
            denom = df_perf_agg.loc[mask_dlp_total, 'dias_laborables_total'].astype(float)
            numer = denom - df_perf_agg.loc[mask_dlp_total, 'Retardos'].astype(float)
            df_perf_agg.loc[mask_dlp_total, 'Índice Puntualidad (%)'] = np.divide(numer.clip(lower=0), denom, out=np.full_like(numer, 100.0), where=denom!=0) * 100
        df_perf_agg['SIC'] = 100.0
        if mask_dlp_total.any():
            denom = df_perf_agg.loc[mask_dlp_total, 'dias_laborables_total'].astype(float)
            numer = denom - (df_perf_agg.loc[mask_dlp_total, 'Faltas'] + df_perf_agg.loc[mask_dlp_total, 'Retardos'] + df_perf_agg.loc[mask_dlp_total, 'Salidas'])
            df_perf_agg.loc[mask_dlp_total, 'SIC'] = np.divide(numer.clip(lower=0), denom, out=np.full_like(numer, 100.0), where=denom!=0) * 100
        df_perf_agg['Tasa Ausentismo (%)'] = 0.0
        if mask_dlp_total.any():
            denom = df_perf_agg.loc[mask_dlp_total, 'dias_laborables_total'].astype(float)
            numer = df_perf_agg.loc[mask_dlp_total, 'Faltas'].astype(float)
            df_perf_agg.loc[mask_dlp_total, 'Tasa Ausentismo (%)'] = np.divide(numer, denom, out=np.zeros_like(numer), where=denom!=0) * 100
        
        df_performance_kpis = df_perf_agg.rename(columns={'employee': 'ID', 'Faltas_Justificadas': 'Faltas Justificadas'})
        perf_cols_needed = ['ID', 'Nombre', 'Faltas Justificadas', 'Tasa Ausentismo (%)', 'Índice Puntualidad (%)', 'Eficiencia Horas (%)', 'SIC']
        for col in perf_cols_needed:
            if col not in df_performance_kpis.columns: df_performance_kpis[col] = 0
        df_performance_kpis = df_performance_kpis[perf_cols_needed]
        performance_kpis_list = df_performance_kpis.round(1).to_dict('records')


        final_data = {
            "branches": datos_agregados,
            "period_summary": period_summary,
            "employee_summary_kpis": summary_kpis_list,
            "employee_performance_kpis": performance_kpis_list
        }
        print("[INFO Dashboard Villas] Datos finales listos para enviar.")
        return {"success": True, "data": final_data}

    except Exception as e:
        import traceback
        print(f"[ERROR Dashboard Villas]: Ocurrió una excepción - {e}")
        traceback.print_exc()
        return {"success": False, "error": f"Error interno: {str(e)}", "data": empty_data}

#Nave
def generar_datos_dashboard_nave(start_date: str, end_date: str) -> dict:
    empty_summary = {"total_attendances": 0, "total_permissions": 0,
                     "total_absences": 0, "total_justified_absences": 0}
    empty_data = {"branches": [], "period_summary": empty_summary,
                  "employee_summary_kpis": [], "employee_performance_kpis": []}

    try:
        manager = AttendanceReportManager()
        processor = AttendanceProcessor()

        print(f"[INFO Dashboard Nave] Obteniendo datos {start_date} a {end_date}")
        codigos, checkins, permisos = manager._prepare_report_data(
            start_date, end_date, sucursal='Nave')
        if not codigos:
            return {"success": True, "data": empty_data}

        print("[INFO Dashboard Nave] Procesando reporte completo...")
        df_detalle, df_resumen = processor.procesar_reporte_completo(
            checkin_data=checkins, permisos_dict=permisos, start_date=start_date,
            end_date=end_date, employee_codes=codigos
        )
        if df_resumen.empty or df_detalle.empty:
            return {"success": True, "data": empty_data}

        print("[INFO Dashboard Nave] Calculando métricas adicionales...")
        df_metricas = calcular_metricas_adicionales(
            df_resumen.copy(), df_detalle.copy())

        print("[INFO Dashboard Nave] Agregando datos por sucursal...")
        datos_agregados = agregar_datos_dashboard_por_sucursal(
            df_metricas.copy())

        print("[INFO Dashboard Nave] Calculando resumen del periodo...")
        total_attendances = int(df_detalle[(df_detalle['horas_esperadas'].dt.total_seconds() > 0) & (
            df_detalle['checados_count'] > 0) & (df_detalle['tiene_permiso'] == False)].shape[0])
        total_permissions = int(df_detalle['tiene_permiso'].sum())
        
        total_unjustified_absences = int(df_resumen['faltas_del_periodo'].sum(
        )) if 'faltas_del_periodo' in df_resumen.columns else 0
        total_justified_absences = int(df_resumen['faltas_justificadas'].sum(
        )) if 'faltas_justificadas' in df_resumen.columns else 0
        total_absences_kpi = total_unjustified_absences + total_justified_absences

        period_summary = {
            "total_attendances": total_attendances,
            "total_permissions": total_permissions,
            "total_absences": total_absences_kpi,
            "total_justified_absences": total_justified_absences
        }
        print(f"[INFO Dashboard Nave] Resumen Periodo: {period_summary}")

        print("[INFO Dashboard Nave] Preparando Resumen Horas por Empleado...")
        
        # --- INICIA CORRECCIÓN DEL ERROR 'str' object ---
        df_summary_kpis_agg = df_resumen.groupby('employee').agg(
            Nombre=('Nombre', 'first'),
            total_horas_trabajadas_td=('total_horas_trabajadas_td', 'sum'),
            total_horas_esperadas_td=('total_horas_esperadas_td', 'sum'), # <-- CORREGIDO
            total_horas_td=('total_horas_td', 'sum'), # <-- CORREGIDO
            total_retardos=('total_retardos', 'sum'),
            faltas_del_periodo=('faltas_del_periodo', 'sum')
        ).reset_index()
        # --- FIN CORRECCIÓN DEL ERROR 'str' object ---

        df_summary_kpis_agg['diferencia_td'] = df_summary_kpis_agg['total_horas_trabajadas_td'] - df_summary_kpis_agg['total_horas_td']
        df_summary_kpis_agg['total_horas_trabajadas'] = df_summary_kpis_agg['total_horas_trabajadas_td'].apply(td_to_str)
        df_summary_kpis_agg['total_horas_esperadas'] = df_summary_kpis_agg['total_horas_esperadas_td'].apply(td_to_str)
        df_summary_kpis_agg['diferencia_HHMMSS'] = df_summary_kpis_agg['diferencia_td'].apply(lambda x: f"-{td_to_str(abs(x))}" if x.total_seconds() < 0 else td_to_str(x))
        df_summary_kpis = df_summary_kpis_agg.copy()
        summary_rename_map = {
            'employee': 'ID', 'Nombre': 'Empleado', 'total_horas_trabajadas': 'Hrs. Trabajadas',
            'total_horas_esperadas': 'Hrs. Planificadas', 'diferencia_HHMMSS': 'Variación',
            'total_retardos': 'Retardos', 'faltas_del_periodo': 'Ausencias'
        }
        final_summary_cols = ['ID', 'Empleado', 'Hrs. Trabajadas',
                              'Hrs. Planificadas', 'Variación', 'Retardos', 'Ausencias']
        df_summary_kpis = df_summary_kpis.rename(columns=summary_rename_map)
        df_summary_kpis = df_summary_kpis[list(
            set(final_summary_cols).intersection(df_summary_kpis.columns))]
        summary_kpis_list = df_summary_kpis.to_dict('records')

        print("[INFO Dashboard Nave] Preparando KPIs de Rendimiento por Empleado...")
        dias_laborables_total = df_detalle[df_detalle['horas_esperadas'].dt.total_seconds() > 0].groupby('employee').size()
        dias_laborables_total.name = 'dias_laborables_total'
        df_perf_agg = df_resumen.groupby('employee').agg(
            Nombre=('Nombre', 'first'), Faltas=('faltas_del_periodo', 'sum'),
            Retardos=('total_retardos', 'sum'), Salidas=('total_salidas_anticipadas', 'sum'),
            Faltas_Justificadas=('faltas_justificadas', 'sum')
        ).reset_index()
        df_perf_agg = df_perf_agg.merge(
            df_summary_kpis_agg[['employee', 'total_horas_trabajadas_td', 'total_horas_td']], on='employee', how='left')
        
        df_perf_agg['employee'] = df_perf_agg['employee'].astype(str)
        dias_laborables_total.index = dias_laborables_total.index.astype(str)
        df_perf_agg = df_perf_agg.merge(dias_laborables_total, on='employee', how='left').fillna(0)
        
        mask_dlp_total = df_perf_agg['dias_laborables_total'] > 0
        total_horas_trabajadas_s = df_perf_agg['total_horas_trabajadas_td'].dt.total_seconds()
        total_horas_netas_s = df_perf_agg['total_horas_td'].dt.total_seconds()
        df_perf_agg['Eficiencia Horas (%)'] = 100.0
        mask_hnp_total = total_horas_netas_s > 0
        if mask_hnp_total.any():
            df_perf_agg.loc[mask_hnp_total, 'Eficiencia Horas (%)'] = np.divide(
                total_horas_trabajadas_s[mask_hnp_total], total_horas_netas_s[mask_hnp_total],
                out=np.full_like(total_horas_trabajadas_s[mask_hnp_total], 100.0), where=total_horas_netas_s[mask_hnp_total]!=0
            ) * 100
        df_perf_agg['Índice Puntualidad (%)'] = 100.0
        if mask_dlp_total.any():
            denom = df_perf_agg.loc[mask_dlp_total, 'dias_laborables_total'].astype(float)
            numer = denom - df_perf_agg.loc[mask_dlp_total, 'Retardos'].astype(float)
            df_perf_agg.loc[mask_dlp_total, 'Índice Puntualidad (%)'] = np.divide(numer.clip(lower=0), denom, out=np.full_like(numer, 100.0), where=denom!=0) * 100
        df_perf_agg['SIC'] = 100.0
        if mask_dlp_total.any():
            denom = df_perf_agg.loc[mask_dlp_total, 'dias_laborables_total'].astype(float)
            numer = denom - (df_perf_agg.loc[mask_dlp_total, 'Faltas'] + df_perf_agg.loc[mask_dlp_total, 'Retardos'] + df_perf_agg.loc[mask_dlp_total, 'Salidas'])
            df_perf_agg.loc[mask_dlp_total, 'SIC'] = np.divide(numer.clip(lower=0), denom, out=np.full_like(numer, 100.0), where=denom!=0) * 100
        df_perf_agg['Tasa Ausentismo (%)'] = 0.0
        if mask_dlp_total.any():
            denom = df_perf_agg.loc[mask_dlp_total, 'dias_laborables_total'].astype(float)
            numer = df_perf_agg.loc[mask_dlp_total, 'Faltas'].astype(float)
            df_perf_agg.loc[mask_dlp_total, 'Tasa Ausentismo (%)'] = np.divide(numer, denom, out=np.zeros_like(numer), where=denom!=0) * 100
        
        df_performance_kpis = df_perf_agg.rename(columns={'employee': 'ID', 'Faltas_Justificadas': 'Faltas Justificadas'})
        perf_cols_needed = ['ID', 'Nombre', 'Faltas Justificadas', 'Tasa Ausentismo (%)', 'Índice Puntualidad (%)', 'Eficiencia Horas (%)', 'SIC']
        for col in perf_cols_needed:
            if col not in df_performance_kpis.columns: df_performance_kpis[col] = 0
        df_performance_kpis = df_performance_kpis[perf_cols_needed]
        performance_kpis_list = df_performance_kpis.round(1).to_dict('records')


        final_data = {
            "branches": datos_agregados,
            "period_summary": period_summary,
            "employee_summary_kpis": summary_kpis_list,
            "employee_performance_kpis": performance_kpis_list
        }
        print("[INFO Dashboard Nave] Datos finales listos para enviar.")
        return {"success": True, "data": final_data}

    except Exception as e:
        import traceback
        print(f"[ERROR Dashboard Nave]: Ocurrió una excepción - {e}")
        traceback.print_exc()
        return {"success": False, "error": f"Error interno: {str(e)}", "data": empty_data}