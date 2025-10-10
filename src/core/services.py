# Imports de Python y librerías externas
from datetime import datetime, timedelta, time
from itertools import product
import pandas as pd
from typing import Dict, List, Tuple

# Imports de Django
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

# Imports de tus propios archivos de la aplicación
from .models import Empleado, AsignacionHorario, Sucursal, Horario, DiaSemana
from .config import (
    TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS,
    TOLERANCIA_RETARDO_MINUTOS,
    DIAS_ESPANOL,
)
from .utils import td_to_str
from .db_postgres_connection import obtener_horario_empleado_completo

def autenticar_usuario(request, email, password):
    try:
        user_obj = User.objects.get(email=email)
        user = authenticate(request, username=user_obj.username, password=password)
        return user
    except User.DoesNotExist:
        return None

def crear_empleado_service(data):
    print("[DEBUG] POST crudo:", dict(data))

    # 1. Crear empleado
    empleado = Empleado.objects.create(
        codigo_frappe=data.get("codigoFrappe"),
        codigo_checador=data.get("codigoChecador"),
        nombre=data.get("nombre"),
        apellido_paterno=data.get("primerApellido"),
        apellido_materno=data.get("segundoApellido"),
        email=data.get("email"),
        tiene_horario_asignado=True
    )
    print(f"[DEBUG] Empleado creado -> empleado_id: {empleado.empleado_id}, Nombre: {empleado.nombre}")

    # 2. Recuperar listas de asignaciones desde el POST
    sucursales = data.getlist("sucursales[]")
    horarios = data.getlist("horarios[]")
    dias = data.getlist("dias[]")

    print("[DEBUG] Sucursales recibidas:", sucursales)
    print("[DEBUG] Horarios recibidos:", horarios)
    print("[DEBUG] Días recibidos:", dias)

    if not sucursales or not horarios or not dias:
        print("[ERROR] No llegaron datos de horarios/sucursales/días")
        return empleado
    
    # 3. Crear asignaciones de horarios
    for sucursal_id, horario_id, dias_str in zip(sucursales, horarios, dias):
        print(f"[DEBUG] Procesando sucursal={sucursal_id}, horario={horario_id}, dias={dias_str}")

        try:  
            
            horario_obj = Horario.objects.get(pk=int(horario_id))
        except Horario.DoesNotExist:
            print(f"[ERROR] Horario con ID {horario_id} no existe")
            continue

        print(f"[DEBUG] Horario -> Entrada: {horario_obj.hora_entrada}, "
              f"Salida: {horario_obj.hora_salida}, Cruza medianoche: {horario_obj.cruza_medianoche}")

        dias_list = dias_str.split(",")  # ej: "1,2,3"
        for dia in dias_list:
            print(
                f"[DEBUG] Insertando AsignacionHorario -> empleado={empleado.empleado_id}, "
                f"sucursal={sucursal_id}, horario={horario_id}, dia_especifico={dia}, "
                f"entrada={horario_obj.hora_entrada}, salida={horario_obj.hora_salida}, "
                f"cruza={horario_obj.cruza_medianoche}"
            )
            AsignacionHorario.objects.create(
                empleado=empleado,
                sucursal_id=int(sucursal_id),
                horario=horario_obj,
                dia_especifico_id=int(dia),
                hora_entrada_especifica=horario_obj.hora_entrada,
                hora_salida_especifica=horario_obj.hora_salida,
                hora_salida_especifica_cruza_medianoche=horario_obj.cruza_medianoche,
            )
    return empleado

def listar_empleados():

    empleados = Empleado.objects.select_related("empleado", "sucursal", "horario").all()

    # Creamos una lista de diccionarios para usar en el template
    lista_empleados = []
    for a in empleados:
        lista_empleados.append(
            {
                "empleado_id": a.empleado.empleado_id,
                "nombre": a.empleado.nombre,
                "apellido_paterno": a.empleado.apellido_paterno,
                "apellido_materno": a.empleado.apellido_materno,
                "email": a.empleado.email,
                "codigo_frappe": a.empleado.codigo_frappe,
                "codigo_checador": a.empleado.codigo_checador,
            }
        )
    return lista_empleados

def crear_horario_service(data):
    return Horario.objects.create(
        hora_entrada=data.get("horaEntrada"),
        hora_salida=data.get("horaSalida"),
        cruza_medianoche=True if data.get("cruzaNoche") == "si" else False,
        descripcion_horario=data.get("descripcionHorario") or "",
    )

#Reporte de Horas
class AttendanceProcessor:
    def process_checkins_to_dataframe(self, checkin_data, start_date, end_date, employee_codes=None):
        df = pd.DataFrame(checkin_data) if checkin_data else pd.DataFrame(columns=['employee', 'time'])
        if 'time' in df.columns and not df.empty:
            df["time"] = pd.to_datetime(df["time"])
            df["dia"] = df["time"].dt.date
            df["checado_time"] = df["time"].dt.time
        
        all_employees = employee_codes if employee_codes else (df["employee"].unique() if not df.empty else [])
        if not all_employees: return pd.DataFrame()

        all_dates = pd.date_range(start=start_date, end=end_date, freq='D').date
        base_df = pd.DataFrame(list(product(all_employees, all_dates)), columns=['employee', 'dia'])

        if not df.empty:
            stats = df.groupby(["employee", "dia"]).agg(
                checado_primero=('checado_time', 'min'),
                checado_ultimo=('checado_time', 'max'),
                checados_count=('time', 'count'),
            ).reset_index()
            def calc_duration(r):
                if r["checados_count"] < 2 or pd.isna(r['checado_primero']): return pd.Timedelta(0)
                d = datetime(2000, 1, 1)
                return datetime.combine(d, r['checado_ultimo']) - datetime.combine(d, r['checado_primero'])
            stats["duration"] = stats.apply(calc_duration, axis=1)
            final_df = base_df.merge(stats, on=['employee', 'dia'], how='left')
        else:
            final_df = base_df
        
        for col in ['duration', 'checados_count', 'checado_primero', 'checado_ultimo']:
            if col not in final_df.columns:
                if col == 'duration': final_df[col] = pd.Timedelta(0)
                elif col == 'checados_count': final_df[col] = 0
                else: final_df[col] = None
        
        final_df['duration'] = final_df['duration'].fillna(pd.Timedelta(0))
        final_df['checados_count'] = final_df['checados_count'].fillna(0).astype(int)
        
        emp_map = {str(e.codigo_frappe): f"{e.nombre} {e.apellido_paterno}" for e in Empleado.objects.filter(codigo_frappe__in=all_employees)}
        final_df['Nombre'] = final_df['employee'].map(emp_map).fillna(final_df['employee'])
        
        final_df["dia_obj"] = pd.to_datetime(final_df["dia"])
        final_df["dia_semana"] = final_df["dia_obj"].dt.day_name()
        return final_df

    # 🚨 FUNCIÓN CORREGIDA ESTRUCTURALMENTE 🚨
    def analizar_asistencia_con_horarios(self, df: pd.DataFrame, start_date_str: str, end_date_str: str) -> pd.DataFrame:
        if df.empty: return df
        print("\n🔄 Analizando horarios (MODIFICACIÓN ESTRUCTURAL FINAL)...")
        
        # 1. Inicialización de columnas
        for col in ["horas_esperadas", "horario_entrada", "horario_salida", "Sucursal"]:
            if 'horas' in col: df[col] = pd.Timedelta(0)
            else: df[col] = None

        employees_to_fetch = df["employee"].unique()
        if len(employees_to_fetch) == 0: return df
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        
        # 🟢 CORRECCIÓN CLAVE: Obtener el horario UNA SOLA VEZ para el rango completo.
        # Esto soluciona los errores de suma de horas para todos los empleados.
        print("   -> Obteniendo horarios para todo el periodo (simplificado)...")
        horarios_periodo = {e: obtener_horario_empleado_completo(e, start_date.strftime('%Y-%m-%d')) for e in employees_to_fetch}
        
        # 2. Iteramos sobre todos los días y empleados en el DataFrame base
        for idx, row in df.iterrows():
            # Usamos el horario obtenido del periodo completo, ignorando la lógica de quincenas
            horario_emp = horarios_periodo.get(row['employee'])
            
            # Si no hay horario asignado o no tiene días con horario, continuamos
            if not horario_emp or horario_emp.get('dias_con_horario', 0) == 0: continue
            
            df.at[idx, 'Sucursal'] = horario_emp.get('sucursal', 'N/A')
            dia_nombre = DIAS_ESPANOL.get(row['dia_semana'], "")
            dia_horario = horario_emp.get('horarios_detallados', {}).get(dia_nombre, {})
            
            if dia_horario.get('tiene_horario'):
                horas_dia = dia_horario.get('horas_totales', 0)
                
                # CÓDIGO DE DIAGNÓSTICO (mantener para ver si la data es correcta)
                if row['employee'] in ['1', '10', '12', '78'] and horas_dia == 0:
                    print(f"🚨 ALERTA 🚨 Emp: {row['employee']}, Día: {row['dia']} no tiene horario asignado (Horas: {horas_dia})")
                
                df.at[idx, 'horas_esperadas'] = timedelta(hours=horas_dia)
                df.at[idx, 'horario_entrada'] = dia_horario.get('entrada')
                df.at[idx, 'horario_salida'] = dia_horario.get('salida')
        
        print("✅ Análisis de horarios completado.")
        return df

    def aplicar_permisos_detallados(self, df: pd.DataFrame, permisos_dict: Dict) -> pd.DataFrame:
        df['horas_permiso'] = pd.Timedelta(0); df['tiene_permiso'] = False
        if df.empty or not permisos_dict: return df
        for emp_code, permisos in permisos_dict.items():
            for fecha, info in permisos.items():
                mask = (df['employee'] == str(emp_code)) & (df['dia'] == pd.to_datetime(fecha).date())
                if mask.any():
                    idx = df[mask].index[0]
                    df.loc[idx, 'tiene_permiso'] = True
                    descuento = df.loc[idx, 'horas_esperadas'] / 2 if info.get('is_half_day', False) else df.loc[idx, 'horas_esperadas']
                    df.loc[idx, 'horas_permiso'] = descuento
        return df

    def calcular_horas_descanso(self, df: pd.DataFrame) -> pd.DataFrame:
        df['horas_descanso'] = pd.Timedelta(0)
        mask = (df['checados_count'] >= 4) & (df['duration'] > pd.Timedelta(0))
        df.loc[mask, 'horas_descanso'] = pd.Timedelta(hours=1)
        return df

    def analizar_incidencias(self, df: pd.DataFrame) -> pd.DataFrame:
        df['falta'] = 0; df['retardo'] = 0; df['salida_anticipada'] = 0
        for idx, row in df.iterrows():
            if row['horas_esperadas'].total_seconds() > 0 and not row['tiene_permiso']:
                if row['checados_count'] == 0:
                    df.at[idx, 'falta'] = 1; continue 
                if row['horario_entrada'] and pd.notna(row['checado_primero']):
                    h_e_str = str(row['horario_entrada']).split('.')[0]
                    h_e = datetime.strptime(h_e_str, '%H:%M:%S' if ':' in h_e_str[3:] else '%H:%M').time()
                    umbral = (datetime.combine(datetime.min, h_e) + timedelta(minutes=TOLERANCIA_RETARDO_MINUTOS)).time()
                    if row['checado_primero'] > umbral: df.at[idx, 'retardo'] = 1
                if row['horario_salida'] and pd.notna(row['checado_ultimo']):
                    h_s_str = str(row['horario_salida']).split('.')[0]
                    h_s = datetime.strptime(h_s_str, '%H:%M:%S' if ':' in h_s_str[3:] else '%H:%M').time()
                    umbral = (datetime.combine(datetime.min, h_s) - timedelta(minutes=TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS)).time()
                    if row['checado_ultimo'] < umbral: df.at[idx, 'salida_anticipada'] = 1
        return df

    def calcular_resumen_final(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty: return pd.DataFrame()
        
        # Corrección: El cálculo de permisos NO debe modificar 'horas_esperadas'
        # Hacemos una copia para el cálculo del resumen.
        df['horas_esperadas_netas'] = df['horas_esperadas'] - df.get('horas_permiso', pd.Timedelta(0))

        df['falta_justificada'] = df.apply(
            lambda x: 1 if x['tiene_permiso'] and x['horas_permiso'] == x['horas_esperadas'] else 0,
            axis=1
        )
        # Asumimos que un episodio de ausencia es igual a una falta
        df['episodio_ausencia_diario'] = df['falta'] 
        # ------------------------------------------------------------------

        agg_dict = {
            'Nombre': 'first', 'Sucursal': 'first', 'duration': 'sum', 'horas_esperadas': 'sum',
            'horas_permiso': 'sum', 'horas_descanso': 'sum', 'falta': 'sum', 'retardo': 'sum', 'salida_anticipada': 'sum',
            'falta_justificada': 'sum', 'episodio_ausencia_diario': 'sum',
        }
        df_resumen = df.groupby('employee').agg(agg_dict).reset_index().rename(columns={
            'duration': 'total_horas_trabajadas_td', 'horas_esperadas': 'total_horas_esperadas_td',
            'horas_permiso': 'total_horas_descontadas_permiso_td', 'horas_descanso': 'total_horas_descanso_td',
            'falta': 'faltas_del_periodo', 
            
            # 2. Renombrar las demás (ya no hay conflicto)
            'retardo': 'total_retardos', 
            'salida_anticipada': 'total_salidas_anticipadas',
            'falta_justificada': 'faltas_justificadas', 
            'episodio_ausencia_diario': 'episodios_ausencia',
        })
        
        # NOTA: Se eliminó el código de inyección temporal de valores, la corrección estructural debe bastar.
        
        df_resumen['total_horas_td'] = df_resumen['total_horas_esperadas_td'] - df_resumen['total_horas_descontadas_permiso_td']
        df_resumen['diferencia_td'] = df_resumen['total_horas_trabajadas_td'] - df_resumen['total_horas_td']
        
        for col in [c for c in df_resumen.columns if '_td' in c]:
            df_resumen[col.replace('_td', '')] = df_resumen[col].apply(td_to_str)
        
        df_resumen['diferencia_HHMMSS'] = df_resumen['diferencia_td'].apply(lambda x: f"-{td_to_str(abs(x))}" if x.total_seconds() < 0 else td_to_str(x))
        df_resumen['total_faltas'] = df_resumen['faltas_del_periodo'] 

        # 🟢 CORRECCIÓN CLAVE: Forzar la conversión a número entero
        df_resumen['total_retardos'] = df_resumen['total_retardos'].fillna(0).astype(int)
        df_resumen['total_salidas_anticipadas'] = df_resumen['total_salidas_anticipadas'].fillna(0).astype(int)
        # -------------------------------------------------------------

        return df_resumen[['employee', 'Nombre', 'Sucursal', 'total_horas_trabajadas', 'total_horas_esperadas', 
                            'total_horas_descontadas_permiso', 'total_horas_descanso', 'total_horas',
                            'diferencia_HHMMSS', 'total_faltas', 'total_retardos', 'total_salidas_anticipadas',
                            'faltas_del_periodo', 
                            'faltas_justificadas', 
                            'episodios_ausencia',]]

    def procesar_reporte_completo(self, checkin_data, permisos_dict, joining_dates_dict, start_date, end_date, employee_codes=None):
        df_detalle = self.process_checkins_to_dataframe(checkin_data, start_date, end_date, employee_codes)
        if df_detalle.empty: return pd.DataFrame(), pd.DataFrame()
        
        df_detalle = self.analizar_asistencia_con_horarios(df_detalle, start_date, end_date)
        df_detalle = self.aplicar_permisos_detallados(df_detalle, permisos_dict)
        df_detalle = self.calcular_horas_descanso(df_detalle)
        df_detalle = self.analizar_incidencias(df_detalle)
        
        df_resumen = self.calcular_resumen_final(df_detalle)
        
        return df_detalle, df_resumen

def generar_reporte_asistencia(checkin_data, permisos_dict, joining_dates_dict, start_date, end_date, employee_codes=None):
    processor = AttendanceProcessor()
    return processor.procesar_reporte_completo(checkin_data, permisos_dict, joining_dates_dict, start_date, end_date, employee_codes)