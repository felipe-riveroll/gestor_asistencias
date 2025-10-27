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
import numpy as np


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

#Reporte de Horas y Lista de Asistencias
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

    def analizar_asistencia_con_horarios(self, df: pd.DataFrame, start_date_str: str, end_date_str: str) -> pd.DataFrame:
        if df.empty: return df
        for col in ["horas_esperadas", "horario_entrada", "horario_salida", "Sucursal"]:
            if 'horas' in col: df[col] = pd.Timedelta(0)
            else: df[col] = None

        employees_to_fetch = df["employee"].unique()
        if len(employees_to_fetch) == 0: return df
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        
        horarios_periodo = {e: obtener_horario_empleado_completo(e, start_date.strftime('%Y-%m-%d')) for e in employees_to_fetch}
        
        for idx, row in df.iterrows():
            horario_emp = horarios_periodo.get(row['employee'])
            if not horario_emp or horario_emp.get('dias_con_horario', 0) == 0: continue
            
            df.at[idx, 'Sucursal'] = horario_emp.get('sucursal', 'N/A')
            dia_nombre = DIAS_ESPANOL.get(row['dia_semana'], "")
            dia_horario = horario_emp.get('horarios_detallados', {}).get(dia_nombre, {})
            
            if dia_horario.get('tiene_horario'):
                horas_dia = dia_horario.get('horas_totales', 0)
                df.at[idx, 'horas_esperadas'] = timedelta(hours=horas_dia)
                df.at[idx, 'horario_entrada'] = dia_horario.get('entrada')
                df.at[idx, 'horario_salida'] = dia_horario.get('salida')
        return df

    def aplicar_permisos_detallados(self, df: pd.DataFrame, permisos_dict: dict) -> pd.DataFrame:
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
        
        df['horas_esperadas_netas'] = df['horas_esperadas'] - df.get('horas_permiso', pd.Timedelta(0))
        df['falta_justificada'] = df.apply(lambda x: 1 if x['tiene_permiso'] and x['horas_permiso'] == x['horas_esperadas'] else 0, axis=1)
        df['episodio_ausencia_diario'] = df['falta'] 

        agg_dict = {
            'Nombre': 'first', 'Sucursal': 'first', 'duration': 'sum', 'horas_esperadas': 'sum',
            'horas_permiso': 'sum', 'horas_descanso': 'sum', 'falta': 'sum', 'retardo': 'sum', 'salida_anticipada': 'sum',
            'falta_justificada': 'sum', 'episodio_ausencia_diario': 'sum',
        }
        df_resumen = df.groupby('employee').agg(agg_dict).reset_index().rename(columns={
            'duration': 'total_horas_trabajadas_td', 'horas_esperadas': 'total_horas_esperadas_td',
            'horas_permiso': 'total_horas_descontadas_permiso_td', 'horas_descanso': 'total_horas_descanso_td',
            'falta': 'faltas_del_periodo', 'retardo': 'total_retardos', 
            'salida_anticipada': 'total_salidas_anticipadas', 'falta_justificada': 'faltas_justificadas', 
            'episodio_ausencia_diario': 'episodios_ausencia',
        })
        
        df_resumen['total_horas_td'] = df_resumen['total_horas_esperadas_td'] - df_resumen['total_horas_descontadas_permiso_td']
        df_resumen['diferencia_td'] = df_resumen['total_horas_trabajadas_td'] - df_resumen['total_horas_td']
        
        for col in [c for c in df_resumen.columns if '_td' in c]:
            df_resumen[col.replace('_td', '')] = df_resumen[col].apply(td_to_str)
        
        df_resumen['diferencia_HHMMSS'] = df_resumen['diferencia_td'].apply(lambda x: f"-{td_to_str(abs(x))}" if x.total_seconds() < 0 else td_to_str(x))
        df_resumen['total_faltas'] = df_resumen['faltas_del_periodo'] 
        df_resumen['total_retardos'] = df_resumen['total_retardos'].fillna(0).astype(int)
        df_resumen['total_salidas_anticipadas'] = df_resumen['total_salidas_anticipadas'].fillna(0).astype(int)

        return df_resumen[['employee', 'Nombre', 'Sucursal', 'total_horas_trabajadas', 'total_horas_esperadas', 
                            'total_horas_descontadas_permiso', 'total_horas_descanso', 'total_horas',
                            'diferencia_HHMMSS', 'total_faltas', 'total_retardos', 'total_salidas_anticipadas',
                            'faltas_del_periodo', 'faltas_justificadas', 'episodios_ausencia',]]

    def calcular_descanso_real_detallado(self, df_checadas_completo: pd.DataFrame) -> pd.DataFrame:
        if df_checadas_completo.empty or 'time' not in df_checadas_completo.columns:
            return pd.DataFrame(columns=['employee', 'dia', 'horas_descanso'])

        df_checadas_completo['time'] = pd.to_datetime(df_checadas_completo['time'])
        grupos = df_checadas_completo.groupby(['employee', 'dia'])
        descansos_calculados = []

        for (empleado, dia), grupo in grupos:
            checadas_ordenadas = grupo.sort_values('time')['time'].tolist()
            total_descanso_dia = timedelta(0)
            if len(checadas_ordenadas) >= 4:
                for i in range(1, len(checadas_ordenadas) - 1, 2):
                    salida_descanso = checadas_ordenadas[i]
                    entrada_descanso = checadas_ordenadas[i+1]
                    total_descanso_dia += (entrada_descanso - salida_descanso)
            
            descansos_calculados.append({
                'employee': empleado, 'dia': dia, 'horas_descanso': total_descanso_dia
            })
        return pd.DataFrame(descansos_calculados)

    def procesar_reporte_completo(self, checkin_data, permisos_dict, start_date, end_date, employee_codes=None):
        df_checadas_original = pd.DataFrame(checkin_data) if checkin_data else pd.DataFrame()
        if not df_checadas_original.empty and 'time' in df_checadas_original.columns:
            df_checadas_original['time'] = pd.to_datetime(df_checadas_original['time'])
            df_checadas_original['dia'] = df_checadas_original['time'].dt.date

        df_detalle = self.process_checkins_to_dataframe(checkin_data, start_date, end_date, employee_codes)
        if df_detalle.empty: return pd.DataFrame(), pd.DataFrame()
        
        df_detalle = self.analizar_asistencia_con_horarios(df_detalle, start_date, end_date)
        df_detalle = self.aplicar_permisos_detallados(df_detalle, permisos_dict)
        
        df_descansos = self.calcular_descanso_real_detallado(df_checadas_original)
        
        if not df_descansos.empty:
            df_descansos['dia'] = pd.to_datetime(df_descansos['dia']).dt.date
            df_detalle = pd.merge(df_detalle, df_descansos, on=['employee', 'dia'], how='left')
            df_detalle['horas_descanso'] = df_detalle['horas_descanso'].fillna(pd.Timedelta(0))
        else:
            df_detalle['horas_descanso'] = pd.Timedelta(0)

        df_detalle = self.analizar_incidencias(df_detalle)
        df_resumen = self.calcular_resumen_final(df_detalle)
        
        return df_detalle, df_resumen

    def pivot_checkins(self, df_checadas: pd.DataFrame) -> pd.DataFrame:
        if df_checadas.empty or 'time' not in df_checadas.columns:
            return pd.DataFrame()
        
        df = df_checadas.copy()
        df['checado_time'] = pd.to_datetime(df['time']).dt.time
        df = df.sort_values(['employee', 'time'])
        df['checkin_rank'] = df.groupby(['employee', 'dia']).cumcount() + 1
        
        df_pivoted = df.pivot_table(index=['employee', 'dia'], columns='checkin_rank', values='checado_time', aggfunc='first').reset_index()
        
        max_checkins = max([col for col in df_pivoted.columns if isinstance(col, int)], default=0)
        rename_dict = {i: f'checado_{i}' for i in range(1, max_checkins + 1)}
        df_pivoted.rename(columns=rename_dict, inplace=True)
        return df_pivoted

    def determinar_observaciones(self, df: pd.DataFrame) -> pd.DataFrame:
        df_copy = df.copy()
        
        first_check = pd.to_datetime(df_copy['checado_primero'].astype(str), errors='coerce', format='%H:%M:%S')
        entry_schedule = pd.to_datetime(df_copy['horario_entrada'].astype(str), errors='coerce', format='%H:%M:%S')

        conditions = [
            df_copy['tiene_permiso'] == True,
            (df_copy['horas_esperadas'].dt.total_seconds() == 0) & (df_copy['checados_count'] == 0),
            df_copy['falta'] == 1,
            (df_copy['retardo'] == 1) & (df_copy['duration'] >= df_copy['horas_esperadas']),
            (first_check - entry_schedule).dt.total_seconds() > (30 * 60),
            df_copy['retardo'] == 1,
            df_copy['salida_anticipada'] == 1,
        ]
        choices = ['Permiso', 'Descanso', 'Falta', 'Cumplió con horas', 'Retardo Mayor', 'Retardo Normal', 'Salida Anticipada']
        df_copy['observacion_incidencia'] = np.select(conditions, choices, default='OK')
        return df_copy

    def procesar_reporte_detalle(self, checkin_data, permisos_dict, start_date, end_date, employee_codes=None):
        df_checadas_original = pd.DataFrame(checkin_data) if checkin_data else pd.DataFrame(columns=['employee', 'time'])
        if not df_checadas_original.empty and 'time' in df_checadas_original.columns:
            df_checadas_original['time'] = pd.to_datetime(df_checadas_original['time'])
            df_checadas_original['dia'] = df_checadas_original['time'].dt.date

        df_detalle = self.process_checkins_to_dataframe(checkin_data, start_date, end_date, employee_codes)
        if df_detalle.empty: return pd.DataFrame()

        df_detalle = self.analizar_asistencia_con_horarios(df_detalle, start_date, end_date)
        df_detalle = self.aplicar_permisos_detallados(df_detalle, permisos_dict)
        df_detalle = self.analizar_incidencias(df_detalle)
        
        df_pivoted = self.pivot_checkins(df_checadas_original)

        if not df_pivoted.empty:
            df_pivoted['employee'] = df_pivoted['employee'].astype(str)
            df_pivoted['dia'] = pd.to_datetime(df_pivoted['dia']).dt.date
            df_detalle = pd.merge(df_detalle, df_pivoted, on=['employee', 'dia'], how='left')

        df_detalle = self.determinar_observaciones(df_detalle)

        for col in ['duration', 'horas_esperadas']:
            if col in df_detalle.columns:
                df_detalle[col] = df_detalle[col].apply(td_to_str)
        
        for col in df_detalle.columns:
            if col.startswith('checado_') or col.startswith('horario_'):
                df_detalle[col] = df_detalle[col].apply(lambda x: x.strftime('%H:%M:%S') if pd.notna(x) and not isinstance(x, str) else x)

        df_detalle['dia_semana'] = df_detalle['dia_semana'].map(DIAS_ESPANOL).fillna(df_detalle['dia_semana'])
        df_detalle['dia'] = df_detalle['dia'].astype(str)
        df_detalle.fillna('-', inplace=True)
        return df_detalle

#Grafica General
def calcular_metricas_adicionales(df_resumen: pd.DataFrame, df_detalle: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula métricas adicionales como Eficiencia, Puntualidad y Bradford por empleado.
    """
    if df_resumen.empty or df_detalle.empty:
        return df_resumen

    # 1. Calcular Eficiencia
    # Convertimos a segundos, manejando división por cero
    total_horas_trabajadas_s = df_resumen['total_horas_trabajadas_td'].dt.total_seconds()
    total_horas_netas_s = df_resumen['total_horas_td'].dt.total_seconds()
    df_resumen['efficiency'] = (total_horas_trabajadas_s / total_horas_netas_s * 100).fillna(0)
    df_resumen['efficiency'] = df_resumen['efficiency'].clip(0, 100) # Aseguramos que no pase de 100%

    # 2. Calcular Puntualidad
    # Contar días laborables por empleado desde el df_detalle
    dias_laborables = df_detalle[df_detalle['horas_esperadas'].dt.total_seconds() > 0].groupby('employee').size()
    dias_laborables.name = 'dias_laborables'
    df_resumen = df_resumen.merge(dias_laborables, on='employee', how='left').fillna(0)
    
    # Puntualidad = (Días laborables - retardos) / Días laborables
    df_resumen['punctuality'] = ((df_resumen['dias_laborables'] - df_resumen['total_retardos']) / df_resumen['dias_laborables'] * 100).fillna(100)
    df_resumen['punctuality'] = df_resumen['punctuality'].clip(0, 100)

    # 3. Calcular Factor Bradford
    # B = S^2 * D (S=episodios de ausencia, D=días totales de ausencia)
    df_resumen['bradford_factor'] = (df_resumen['episodios_ausencia'] ** 2) * df_resumen['faltas_del_periodo']

    return df_resumen


def agregar_datos_dashboard_por_sucursal(df_metricas: pd.DataFrame) -> List[Dict]:
    """
    Agrupa el DataFrame con métricas por sucursal y calcula los KPIs para el dashboard.
    """
    if df_metricas.empty or 'Sucursal' not in df_metricas.columns:
        return []

    # Agrupar por sucursal y agregar los datos
    df_sucursales = df_metricas.groupby('Sucursal').agg(
        employees=('employee', 'count'),
        efficiency=('efficiency', 'mean'),
        punctuality=('punctuality', 'mean'),
        avgBradford=('bradford_factor', 'mean'),
        absences=('faltas_del_periodo', 'sum')
    ).reset_index()

    # Renombrar la columna 'Sucursal' a 'name' para que coincida con el JS
    df_sucursales.rename(columns={'Sucursal': 'name'}, inplace=True)
    
    # Añadimos un SIC promedio (usando eficiencia como proxy, ya que no está definido)
    df_sucursales['avgSIC'] = df_sucursales['efficiency']
    
    # Formatear a dos decimales y convertir a lista de diccionarios
    for col in ['efficiency', 'punctuality', 'avgBradford', 'avgSIC']:
        df_sucursales[col] = df_sucursales[col].round(2)
        
    return df_sucursales.to_dict('records')