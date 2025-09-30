from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta, time
from collections import defaultdict
from itertools import product
import pandas as pd
from typing import Dict, List
import pytz

from .db_postgres_connection import obtener_horario_empleado as obtener_horario_real

def obtener_horario_empleado(employee_code, dia_semana=None, es_primera_quincena=None, cache=None):
    """
    Función wrapper para compatibilidad con 4 argumentos
    """
    # Solo pasamos el primer argumento a la función real
    return obtener_horario_real(employee_code)
# ===== FIN PARCHE =====

# Imports de tus propios archivos (locales)
from .models import Empleado, AsignacionHorario, Sucursal, Horario
from .config import (
    POLITICA_PERMISOS,
    PERDONAR_TAMBIEN_FALTA_INJUSTIFICADA,
    TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS,
    TOLERANCIA_RETARDO_MINUTOS,
    UMBRAL_FALTA_INJUSTIFICADA_MINUTOS,
    DIAS_ESPANOL,
    GRACE_MINUTES,
)
from .utils import td_to_str, safe_timedelta
from .db_postgres_connection import obtener_horario_empleado

def autenticar_usuario(request, email, password):
    try:
        user_obj = User.objects.get(email=email)
        user = authenticate(request, username=user_obj.username, password=password)
        return user
    except User.DoesNotExist:
        return None

def crear_empleado_service(data):
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

    # 2. Crear asignación (si existen sucursal y horario)
    sucursal_id = data.get("sucursal")
    horario_id = data.get("horario")

    if sucursal_id and horario_id:
        sucursal = Sucursal.objects.get(pk=int(sucursal_id))
        horario = Horario.objects.get(pk=int(horario_id))

        # 2. Crear asignación con datos extra del horario
        AsignacionHorario.objects.create(
            empleado=empleado,
            sucursal=sucursal,
            horario=horario,
            es_primera_quincena=True,
            hora_entrada_especifica=horario.hora_entrada,
            hora_salida_especifica=horario.hora_salida,
            hora_salida_especifica_cruza_medianoche=horario.cruza_medianoche
        )
    return empleado

def listar_empleados():

    empleados = Empleado.objects.select_related(
        'empleado', 'sucursal', 'horario'
    ).all()

    # Creamos una lista de diccionarios para usar en el template
    lista_empleados = []
    for a in empleados:
        lista_empleados.append({
            'empleado_id': a.empleado.empleado_id,
            'nombre': a.empleado.nombre,
            'apellido_paterno': a.empleado.apellido_paterno,
            'apellido_materno': a.empleado.apellido_materno,
            'email': a.empleado.email,
            'codigo_frappe': a.empleado.codigo_frappe,
            'codigo_checador': a.empleado.codigo_checador
        })
    return lista_empleados

def crear_horario_service(data):
    return Horario.objects.create(
        hora_entrada=data.get("horaEntrada"),
        hora_salida=data.get("horaSalida"),
        cruza_medianoche=True if data.get("cruzaNoche") == "si" else False,
        descripcion_horario=data.get("descripcionHorario") or ""
    )

# Reporte de horas
"""
Data processing module for the attendance reporting system.
Contains all core business logic for processing check-ins, schedules, and generating analysis.
"""
def transformar_horarios_db_a_cache(horarios_db: List[Dict]) -> List[Dict]:
    """
    Toma los datos crudos de la BD y los transforma al formato esperado por buscar_horario_en_cache.
    - Renombra 'horario_entrada' a 'hora_entrada'.
    - Renombra 'horario_salida' a 'hora_salida'.
    """
    if not horarios_db:
        return []

    print(f"🔄 Transformando {len(horarios_db)} registros de horarios de la BD al formato de cache...")
   
    horarios_transformados = []
    for registro in horarios_db:
        # Crea una copia para no modificar el original
        nuevo_registro = dict(registro)
       
        # Itera sobre los días de la semana
        for dia in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']:
            horario_dia = nuevo_registro.get(dia)
            if isinstance(horario_dia, dict):
                # Renombra las claves si existen
                if 'horario_entrada' in horario_dia:
                    horario_dia['hora_entrada'] = horario_dia.pop('horario_entrada')
                if 'horario_salida' in horario_dia:
                    horario_dia['hora_salida'] = horario_dia.pop('horario_salida')
       
        horarios_transformados.append(nuevo_registro)
       
    print("✅ Transformación de horarios completada.")
    return horarios_transformados

class AttendanceProcessor:
    """Main class for processing attendance data and applying business rules."""

    def __init__(self):
        """Initialize the attendance processor."""
        pass

    def process_checkins_to_dataframe(
        self, checkin_data: List[Dict], start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Creates a base DataFrame with one row per employee and day."""
        if not checkin_data:
            return pd.DataFrame()

        df = pd.DataFrame(checkin_data)
        df["time"] = pd.to_datetime(df["time"])
        df["dia"] = df["time"].dt.date
        df["checado_time"] = df["time"].dt.strftime("%H:%M:%S")

        employee_map = (
            df[["employee", "employee_name"]]
            .drop_duplicates()
            .rename(columns={"employee_name": "Nombre"})
        )

        # Calculate duration as Timedelta and save in duration column
        df_hours = (
            df.groupby(["employee", "dia"])["time"].agg(["min", "max"]).reset_index()
        )
        df_hours["duration"] = df_hours["max"] - df_hours["min"]

        # Keep duration as Timedelta, only convert to string for compatibility
        df_hours["horas_trabajadas"] = df_hours["duration"].apply(
            lambda x: td_to_str(x) if pd.notna(x) else "00:00:00"
        )

        df["checado_rank"] = df.groupby(["employee", "dia"]).cumcount() + 1
        df_pivot = df.pivot_table(
            index=["employee", "dia"],
            columns="checado_rank",
            values="checado_time",
            aggfunc="first",
        )
        if not df_pivot.empty:
            df_pivot.columns = [
                f"checado_{i}" for i in range(1, len(df_pivot.columns) + 1)
            ]

        all_employees = df["employee"].unique()
        all_dates = pd.to_datetime(pd.date_range(start=start_date, end=end_date)).date
        base_df = pd.DataFrame(
            list(product(all_employees, all_dates)), columns=["employee", "dia"]
        )

        daily_df = pd.merge(
            base_df, df_pivot.reset_index(), on=["employee", "dia"], how="left"
        )
        final_df = pd.merge(daily_df, employee_map, on="employee", how="left")
        df_hours["dia"] = pd.to_datetime(df_hours["dia"]).dt.date
        final_df = pd.merge(
            final_df,
            df_hours[["employee", "dia", "duration", "horas_trabajadas"]],
            on=["employee", "dia"],
            how="left",
        )

        final_df["dia_semana"] = (
            pd.to_datetime(final_df["dia"]).dt.day_name().map(DIAS_ESPANOL)
        )
        final_df["dia_iso"] = pd.to_datetime(final_df["dia"]).dt.weekday + 1

        return final_df

    def calcular_horas_descanso(self, df_dia) -> timedelta:
        """
        Calculates break hours based on check-ins for the day.
        Only calculates break if there are 4+ check-ins and the break times
        are different from entry/exit times.
        """
        # Get all available check-in columns
        if hasattr(df_dia, "columns"):
            # It's a DataFrame
            checado_cols = [col for col in df_dia.columns if col.startswith("checado_")]
        else:
            # It's a Series
            checado_cols = [col for col in df_dia.index if col.startswith("checado_")]

        if len(checado_cols) < 4:
            return timedelta(0)

        # Get check-in values for this day/employee
        checados = []
        for col in checado_cols:
            if hasattr(df_dia, "columns"):
                valor = df_dia.get(col)
            else:
                valor = df_dia.get(col, None)
            if pd.notna(valor) and valor is not None and valor != "---":
                checados.append(valor)

        # Filter check-ins with dropna() and require len(checados) >= 4
        checados = [c for c in checados if pd.notna(c)]
        if len(checados) < 4:
            return timedelta(0)

        # Sort check-ins chronologically
        checados_ordenados = sorted(checados, key=lambda x: str(x))
       
        # Get first and last check-in times (entry and exit)
        hora_entrada = checados_ordenados[0]
        hora_salida = checados_ordenados[-1]

        # Calculate multiple break intervals (pairs 1-2, 3-4, etc.)
        total_descanso = timedelta(0)

        try:
            # Process pairs of check-ins to calculate breaks
            for i in range(1, len(checados_ordenados) - 1, 2):
                if i + 1 < len(checados_ordenados):
                    # Take second and third check-in of the pair
                    segundo_checado = checados_ordenados[i]
                    tercer_checado = checados_ordenados[i + 1]
                   
                    # Skip if break times are same as entry or exit times
                    if (segundo_checado == hora_entrada or segundo_checado == hora_salida or
                        tercer_checado == hora_entrada or tercer_checado == hora_salida):
                        continue

                    # Convert to datetime to calculate difference
                    if isinstance(segundo_checado, time):
                        segundo_dt = datetime.combine(datetime.today(), segundo_checado)
                    else:
                        segundo_dt = datetime.strptime(str(segundo_checado), "%H:%M:%S")

                    if isinstance(tercer_checado, time):
                        tercer_dt = datetime.combine(datetime.today(), tercer_checado)
                    else:
                        tercer_dt = datetime.strptime(str(tercer_checado), "%H:%M:%S")

                    # Calculate difference
                    descanso_intervalo = tercer_dt - segundo_dt

                    # Only add if difference is positive and reasonable (more than 5 minutes)
                    if descanso_intervalo.total_seconds() > 300:  # More than 5 minutes
                        total_descanso += descanso_intervalo

            return total_descanso

        except (ValueError, TypeError):
            return timedelta(0)

    def aplicar_calculo_horas_descanso(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies break hours calculation to the entire DataFrame.
        NO adjustments are made to expected or worked hours - only calculates break time.
        """
        if df.empty:
            return df

        print("🔄 Calculando horas de descanso...")

        # Create columns for break hours as Timedelta
        df["horas_descanso_td"] = pd.Timedelta(0)
        df["horas_descanso"] = "00:00:00"  # For CSV compatibility

        # Save original values (no longer needed for adjustments, but kept for reference)
        df["horas_trabajadas_originales"] = df["horas_trabajadas"].copy()
        df["horas_esperadas_originales"] = df["horas_esperadas"].copy()

        # Convert duration to Timedelta if it exists
        if "duration" in df.columns:
            df["duration_td"] = df["duration"].fillna(pd.Timedelta(0))
        else:
            df["duration_td"] = pd.Timedelta(0)

        total_dias_con_descanso = 0

        for index, row in df.iterrows():
            # Calculate break hours for this row
            horas_descanso_td = self.calcular_horas_descanso(row)

            if horas_descanso_td > timedelta(0):
                df.at[index, "horas_descanso_td"] = horas_descanso_td
                df.at[index, "horas_descanso"] = td_to_str(horas_descanso_td)
                total_dias_con_descanso += 1

        print(f"✅ Se calcularon horas de descanso para {total_dias_con_descanso} días")
        return df

    def procesar_horarios_con_medianoche(
        self, df: pd.DataFrame, cache_horarios: Dict
    ) -> pd.DataFrame:
        """
        Reorganiza las marcas de entrada/salida para turnos que cruzan medianoche.
       
        Para turnos nocturnos (ej: 18:00 → 02:00):
        1. Determina la "fecha de turno" usando la hora de entrada
        2. Agrupa marcas por empleado + fecha de turno
        3. Mantiene primera marca como entrada y última marca como salida
        4. Calcula horas trabajadas considerando el cruce de medianoche
       
        IMPORTANTE: La lógica de ventana de gracia (GRACE_MINUTES) solo aplica cuando
        cruza_medianoche=True. Para turnos normales, las marcas se asignan al día
        calendario correspondiente.
        """
        print("\n🔄 Procesando turnos que cruzan medianoche...")
       
        if df.empty:
            return df
           
        # Crear una copia del DataFrame original para trabajar
        df_proc = df.copy()
       
        # Agregar columna es_primera_quincena si no existe
        if 'es_primera_quincena' not in df_proc.columns:
            df_proc['es_primera_quincena'] = df_proc['dia'].apply(lambda x: x.day <= 15)
       
        # Función para mapear la fecha de turno correcta
        def map_shift_date(checada_time, entrada, salida, cruza_medianoche, dia_original):
            """
            Adjust logic: treat times within grace window after salida as belonging to previous day.
            """
            if not cruza_medianoche:
                return dia_original
            try:
                datetime.strptime(entrada, "%H:%M").time()
                salida_time = datetime.strptime(salida, "%H:%M").time()
                checada_time_obj = datetime.strptime(checada_time, "%H:%M:%S").time()
                # Grace window after scheduled salida
                limite_gracia = (datetime.combine(dia_original, salida_time) + timedelta(minutes=GRACE_MINUTES)).time()
                # If checada is between salida and limite_gracia inclusive, assign to previous day
                if salida_time <= checada_time_obj <= limite_gracia:
                    return dia_original - timedelta(days=1)
                else:
                    return dia_original
            except (ValueError, TypeError):
                return dia_original

        # Función para detectar si un grupo de marcas solo contiene salidas
        def is_only_checkout(marks, entrada_teorica, salida_teorica):
            """
            Determina si un grupo de marcas solo contiene registros de salida.
           
            Args:
                marks: lista de timestamps ordenados
                entrada_teorica: hora de entrada programada (time object)
                salida_teorica: hora de salida programada (time object)
               
            Returns:
                True si no hay marca >= entrada_teorica y < 23:59:59 del shift_date
            """
            try:
                entrada_time = datetime.strptime(entrada_teorica, "%H:%M").time()
                datetime.strptime(salida_teorica, "%H:%M").time()
               
                # Verificar si todas las marcas están antes de la hora de entrada programada
                # o dentro de la ventana de gracia de la salida
                for marca in marks:
                    marca_time = datetime.strptime(marca, "%H:%M:%S").time()
                   
                    # Si hay una marca después de la entrada programada y antes de medianoche, no es solo salida
                    if marca_time >= entrada_time and marca_time < time(23, 59, 59):
                        return False
               
                # Si llegamos aquí, todas las marcas están antes de la entrada o en la ventana de gracia
                return True
            except (ValueError, TypeError):
                return False
       
        # Procesar turnos nocturnos dia por dia
        marcas_list = []
        turnos_procesados = set()  # Para rastrear qué turnos fueron procesados
       
        # Primero, identificar todos los empleados con turnos nocturnos y recolectar todas sus marcas por día
        empleados_turnos_nocturnos = {}
       
        for index, row in df_proc.iterrows():
            empleado = row['employee']
            dia = row['dia']
           
            # Obtener horario del empleado para este día
            horario = obtener_horario_empleado(
                str(empleado),
                row['dia_iso'],
                row['es_primera_quincena'],
                cache_horarios
            )
           
            # Si no hay horario para este día, buscar en el día anterior
            # para casos donde las marcas tardías caen en días sin horario programado
            entrada = None
            salida = None
            cruza_medianoche = False
           
            if horario:
                entrada = horario.get('hora_entrada')
                salida = horario.get('hora_salida')
                cruza_medianoche = horario.get('cruza_medianoche', False)
            else:
                # Buscar horario del día anterior que pueda ser nocturno
                dia_anterior = dia - timedelta(days=1)
                dia_anterior_iso = dia_anterior.weekday() + 1
               
                horario_anterior = obtener_horario_empleado(
                    str(empleado),
                    dia_anterior_iso,
                    row['es_primera_quincena'],
                    cache_horarios
                )
               
                if horario_anterior and horario_anterior.get('cruza_medianoche', False):
                    entrada = horario_anterior.get('hora_entrada')
                    salida = horario_anterior.get('hora_salida')
                    cruza_medianoche = True
           
            # Solo procesar si hay un turno nocturno (ya sea del día actual o del anterior)
            if not cruza_medianoche:
                continue
           
            # Inicializar empleado si no existe
            if empleado not in empleados_turnos_nocturnos:
                empleados_turnos_nocturnos[empleado] = {}
           
            # Recolectar todas las marcas del día
            checadas_dia = []
            for j in range(1, 10):
                col_checado = f'checado_{j}'
                if col_checado in row and pd.notna(row[col_checado]):
                    # Crear un horario simulado si es necesario
                    horario_para_marca = horario or {
                        'hora_entrada': entrada,
                        'hora_salida': salida,
                        'cruza_medianoche': cruza_medianoche,
                        'horas_totales': 8.0
                    }
                   
                    checadas_dia.append({
                        'time': row[col_checado],
                        'day': dia,
                        'entrada_prog': entrada,
                        'salida_prog': salida,
                        'horario': horario_para_marca
                    })
           
            empleados_turnos_nocturnos[empleado][dia] = checadas_dia
       
        # Ahora procesar cada empleado para determinar qué marcas pertenecen a qué turno
        for empleado, dias_marcas in empleados_turnos_nocturnos.items():
            dias_ordenados = sorted(dias_marcas.keys())
           
            for i, dia_actual in enumerate(dias_ordenados):
                marcas_dia = dias_marcas[dia_actual]
                if not marcas_dia:
                    continue
                   
                # Obtener horario del día actual
                horario_actual = marcas_dia[0]['horario']
                entrada = horario_actual.get('hora_entrada')
                salida = horario_actual.get('hora_salida')
               
                try:
                    entrada_time = datetime.strptime(entrada, "%H:%M").time()
                    salida_time = datetime.strptime(salida, "%H:%M").time()
                except (ValueError, TypeError):
                    continue
               
                # Separar marcas del día actual en entrada (antes de medianoche) y salida (después de medianoche)
                marcas_entrada = []  # Marcas >= hora_entrada
                marcas_salida_posibles = []  # Marcas tempranas que podrían ser salida del turno anterior
               
                for marca_info in marcas_dia:
                    try:
                        marca_time = datetime.strptime(marca_info['time'], "%H:%M:%S").time()
                       
                        # Si la marca es después de la hora de entrada programada, es entrada del turno actual
                        if marca_time >= entrada_time:
                            marcas_entrada.append(marca_info)
                        else:
                            # Marca temprana que podría ser salida del turno anterior
                            marcas_salida_posibles.append(marca_info)
                    except (ValueError, TypeError):
                        continue
               
                # Procesar marcas de entrada para el turno actual
                for marca_info in marcas_entrada:
                    marcas_list.append({
                        'employee': empleado,
                        'marca_time': marca_info['time'],
                        'fecha_turno': dia_actual,
                        'entrada_programada': entrada,
                        'salida_programada': salida,
                        'cruza_medianoche': True,
                        'dia_original': dia_actual
                    })
                    turnos_procesados.add((empleado, dia_actual))
               
                # Procesar marcas de salida posibles para el turno anterior
                if marcas_salida_posibles and i > 0:
                    dia_anterior = dias_ordenados[i-1]
                   
                    # Verificar si hay un turno nocturno el día anterior
                    if dia_anterior in dias_marcas:
                        # Buscar la marca más tardía dentro de la ventana de gracia como salida del turno anterior
                        limite_gracia = (datetime.combine(datetime.now().date(), salida_time) +
                                       timedelta(minutes=GRACE_MINUTES)).time()
                       
                        mejor_salida = None
                        marcas_restantes = []
                       
                        for marca_info in marcas_salida_posibles:
                            try:
                                marca_time = datetime.strptime(marca_info['time'], "%H:%M:%S").time()
                                if marca_time <= limite_gracia:
                                    if mejor_salida is None or marca_time > datetime.strptime(mejor_salida['time'], "%H:%M:%S").time():
                                        if mejor_salida is not None:
                                            marcas_restantes.append(mejor_salida)
                                        mejor_salida = marca_info
                                    else:
                                        marcas_restantes.append(marca_info)
                                else:
                                    marcas_restantes.append(marca_info)
                            except (ValueError, TypeError):
                                marcas_restantes.append(marca_info)
                       
                        # Asignar la mejor salida al turno anterior
                        if mejor_salida:
                            marcas_list.append({
                                'employee': empleado,
                                'marca_time': mejor_salida['time'],
                                'fecha_turno': dia_anterior,
                                'entrada_programada': entrada,
                                'salida_programada': salida,
                                'cruza_medianoche': True,
                                'dia_original': dia_actual
                            })
                            turnos_procesados.add((empleado, dia_anterior))
                       
                        # Las marcas restantes se quedan en el día actual
                        for marca_info in marcas_restantes:
                            marcas_list.append({
                                'employee': empleado,
                                'marca_time': marca_info['time'],
                                'fecha_turno': dia_actual,
                                'entrada_programada': entrada,
                                'salida_programada': salida,
                                'cruza_medianoche': True,
                                'dia_original': dia_actual
                            })
                    else:
                        # No hay turno anterior, todas las marcas se quedan en el día actual
                        for marca_info in marcas_salida_posibles:
                            marcas_list.append({
                                'employee': empleado,
                                'marca_time': marca_info['time'],
                                'fecha_turno': dia_actual,
                                'entrada_programada': entrada,
                                'salida_programada': salida,
                                'cruza_medianoche': True,
                                'dia_original': dia_actual
                            })
                            turnos_procesados.add((empleado, dia_actual))
                else:
                    # No hay día anterior o no hay marcas de salida posibles
                    for marca_info in marcas_salida_posibles:
                        marcas_list.append({
                            'employee': empleado,
                            'marca_time': marca_info['time'],
                            'fecha_turno': dia_actual,
                            'entrada_programada': entrada,
                            'salida_programada': salida,
                            'cruza_medianoche': True,
                            'dia_original': dia_actual
                        })
                        turnos_procesados.add((empleado, dia_actual))
       
        if not marcas_list:
            print("⚠️ No se encontraron turnos nocturnos para procesar")
            return df_proc
           
        # Crear DataFrame de marcas
        df_marcas = pd.DataFrame(marcas_list)
       
        # Agrupar por empleado y fecha de turno, manteniendo todas las marcas
        df_marcas = pd.DataFrame(marcas_list)
        df_marcas = df_marcas.sort_values(['employee', 'fecha_turno', 'marca_time'])
       
       
        # Crear DataFrame de resultados procesados
        resultados = []
       
        for (empleado, fecha_turno), grupo in df_marcas.groupby(['employee', 'fecha_turno']):
            if len(grupo) < 1:
                continue  # Necesitamos al menos una marca
               
            # Obtener horario para determinar entrada y salida programadas
            entrada_prog = grupo.iloc[0]['entrada_programada']
            salida_prog = grupo.iloc[0]['salida_programada']
           
            try:
                datetime.strptime(entrada_prog, "%H:%M").time()
                datetime.strptime(salida_prog, "%H:%M").time()
            except (ValueError, TypeError):
                continue
           
            # Ordenar por tiempo para obtener todas las marcas
            grupo_ordenado = grupo.sort_values('marca_time')
            marcas_times = grupo_ordenado['marca_time'].tolist()
           
            # Verificar si es un caso de "solo salida" para turnos nocturnos
            if grupo.iloc[0]['cruza_medianoche']:
                is_only_checkout(marcas_times, entrada_prog, salida_prog)
           
            # Para mantener la compatibilidad con los tests, crear entrada con todas las marcas organizadas
            resultado = {
                'employee': empleado,
                'dia': fecha_turno,
                'entrada_programada': entrada_prog,
                'salida_programada': salida_prog,
                'cruza_medianoche': grupo.iloc[0]['cruza_medianoche'],
                'dia_original': grupo.iloc[0]['dia_original']
            }
           
            # Limpiar todas las columnas de checado
            for j in range(1, 10):
                resultado[f'checado_{j}'] = None
           
            # Para turnos nocturnos, decidir si usar entrada/salida o todas las marcas
            if grupo.iloc[0]['cruza_medianoche']:
                # Separar marcas en noche (>= 12:00) y madrugada (< 12:00)
                marcas_noche = []
                marcas_madrugada = []
               
                for marca_time in marcas_times:
                    try:
                        marca_obj = datetime.strptime(marca_time, "%H:%M:%S").time()
                        if marca_obj >= datetime.strptime("12:00:00", "%H:%M:%S").time():
                            marcas_noche.append(marca_time)
                        else:
                            marcas_madrugada.append(marca_time)
                    except (ValueError, TypeError):
                        marcas_noche.append(marca_time)
               
                # Ordenar cada grupo
                marcas_noche.sort()
                marcas_madrugada.sort()
               
                # Si hay marcas tanto de noche como de madrugada, es un turno completo -> entrada/salida
                # Si solo hay marcas de un tipo, mostrar todas las marcas secuencialmente
                if marcas_noche and marcas_madrugada:
                    # Turno completo: entrada = primera noche, salida = última madrugada
                    resultado['checado_1'] = marcas_noche[0]
                    resultado['checado_2'] = marcas_madrugada[-1]
                else:
                    # Solo marcas de un tipo: mostrar todas secuencialmente
                    marcas_ordenadas = marcas_noche + marcas_madrugada
                    for i, marca_time in enumerate(marcas_ordenadas, 1):
                        if i <= 9:
                            resultado[f'checado_{i}'] = marca_time
            else:
                # Para turnos normales, asignar todas las marcas en orden
                for i, marca_time in enumerate(marcas_times, 1):
                    if i <= 9:
                        resultado[f'checado_{i}'] = marca_time
           
            # Calcular horas trabajadas usando checado_1 y checado_2
            try:
                entrada_mark = resultado.get('checado_1')
                salida_mark = resultado.get('checado_2')
               
                if not entrada_mark and not salida_mark:
                    horas_trabajadas = timedelta(0)
                    observaciones = ["Sin marcas de asistencia"]
                elif not entrada_mark:
                    # Caso de solo salida: horas trabajadas = 0
                    horas_trabajadas = timedelta(0)
                    observaciones = ["Falta registro de entrada"]
                elif not salida_mark:
                    # Caso de solo entrada: horas trabajadas = 0
                    horas_trabajadas = timedelta(0)
                    observaciones = ["Falta registro de salida"]
                else:
                    # Caso normal: calcular diferencia entre entrada y salida
                    entrada_time = datetime.strptime(entrada_mark, "%H:%M:%S").time()
                    salida_time = datetime.strptime(salida_mark, "%H:%M:%S").time()
                   
                    inicio = datetime.combine(fecha_turno, entrada_time)
                   
                    # Para turnos que cruzan medianoche, ajustar la salida
                    if grupo.iloc[0]['cruza_medianoche'] and salida_time < entrada_time:
                        fin = datetime.combine(fecha_turno + timedelta(days=1), salida_time)
                    else:
                        fin = datetime.combine(fecha_turno, salida_time)
                   
                    horas_trabajadas = fin - inicio
                    observaciones = []
               
                resultado['duration'] = horas_trabajadas
                resultado['horas_trabajadas'] = td_to_str(horas_trabajadas)
                resultado['observaciones'] = '; '.join(observaciones) if observaciones else None
               
                resultados.append(resultado)
               
            except (ValueError, TypeError) as e:
                print(f"Error calculando horas para empleado {empleado}: {e}")
                continue
       
        if not resultados:
            print("⚠️ No se pudieron procesar turnos nocturnos")
            return df_proc
           
        # Crear DataFrame de resultados
        df_resultados = pd.DataFrame(resultados)
       
        # Actualizar el DataFrame original con los resultados procesados
        for index, resultado in df_resultados.iterrows():
            # Buscar la fila correspondiente en el DataFrame original usando la fecha del turno
            mask = (df_proc['employee'] == resultado['employee']) & \
                   (df_proc['dia'] == resultado['dia'])
           
            if mask.any():
                idx_original = df_proc[mask].index[0]
               
                # Limpiar todas las checadas existentes solo para el turno nocturno procesado
                for j in range(1, 10):
                    col_checado = f'checado_{j}'
                    if col_checado in df_proc.columns:
                        df_proc.loc[idx_original, col_checado] = None
               
                # Asignar entrada y salida procesadas
                df_proc.loc[idx_original, 'checado_1'] = resultado['checado_1']
                df_proc.loc[idx_original, 'checado_2'] = resultado['checado_2']
                df_proc.loc[idx_original, 'duration'] = resultado['duration']
                df_proc.loc[idx_original, 'horas_trabajadas'] = resultado['horas_trabajadas']
               
                # Asignar observaciones si existen
                if 'observaciones' in resultado and resultado['observaciones']:
                    if 'observaciones' not in df_proc.columns:
                        df_proc['observaciones'] = None
                    df_proc.loc[idx_original, 'observaciones'] = resultado['observaciones']
            else:
                # Si no existe la fila para esta fecha de turno, crearla
                # Esto puede pasar cuando las marcas se reasignan a un día anterior
                fila_original = df_proc[df_proc['employee'] == resultado['employee']].iloc[0].copy()
                fila_original['dia'] = resultado['dia']
                fila_original['dia_iso'] = resultado['dia'].weekday() + 1
                fila_original['es_primera_quincena'] = resultado['dia'].day <= 15
               
                # Limpiar todas las checadas
                for j in range(1, 10):
                    col_checado = f'checado_{j}'
                    if col_checado in fila_original:
                        fila_original[col_checado] = None
               
                # Asignar entrada y salida procesadas
                fila_original['checado_1'] = resultado['checado_1']
                fila_original['checado_2'] = resultado['checado_2']
                fila_original['duration'] = resultado['duration']
                fila_original['horas_trabajadas'] = resultado['horas_trabajadas']
               
                # Asignar observaciones si existen  
                if 'observaciones' in resultado and resultado['observaciones']:
                    if 'observaciones' not in fila_original:
                        fila_original['observaciones'] = None
                    fila_original['observaciones'] = resultado['observaciones']
               
                # Agregar la nueva fila al DataFrame
                df_proc = pd.concat([df_proc, fila_original.to_frame().T], ignore_index=True)
       
        # Limpiar marcas de días originales que fueron completamente procesadas y reasignadas
        for index, resultado in df_resultados.iterrows():
            # Si la fecha del turno es diferente al día original, necesitamos limpiar las marcas del día original
            # que fueron reasignadas al turno
            if resultado['dia'] != resultado['dia_original']:
                mask_original = (df_proc['employee'] == resultado['employee']) & \
                               (df_proc['dia'] == resultado['dia_original'])
               
                if mask_original.any():
                    idx_original = df_proc[mask_original].index[0]
                   
                    # Obtener todas las marcas que fueron reasignadas a este turno
                    marcas_reasignadas = []
                    for marca_info in marcas_list:
                        if (marca_info['employee'] == resultado['employee'] and
                            marca_info['fecha_turno'] == resultado['dia'] and
                            marca_info['dia_original'] == resultado['dia_original']):
                            marcas_reasignadas.append(marca_info['marca_time'])
                   
                    # Limpiar solo las marcas que fueron reasignadas, mantener las que corresponden al día original
                    for j in range(1, 10):
                        col_checado = f'checado_{j}'
                        if col_checado in df_proc.columns and pd.notna(df_proc.loc[idx_original, col_checado]):
                            # Si esta marca fue reasignada, limpiarla
                            if df_proc.loc[idx_original, col_checado] in marcas_reasignadas:
                                df_proc.loc[idx_original, col_checado] = None
                   
                    # Reorganizar las marcas restantes
                    marcas_restantes = []
                    for j in range(1, 10):
                        col_checado = f'checado_{j}'
                        if col_checado in df_proc.columns and pd.notna(df_proc.loc[idx_original, col_checado]):
                            marcas_restantes.append(df_proc.loc[idx_original, col_checado])
                            df_proc.loc[idx_original, col_checado] = None
                   
                    # Reasignar las marcas restantes desde checado_1
                    for i, marca in enumerate(marcas_restantes, 1):
                        if i <= 9:
                            df_proc.loc[idx_original, f'checado_{i}'] = marca
                   
                    # Si no quedan marcas, limpiar duration y horas_trabajadas
                    if not marcas_restantes:
                        df_proc.loc[idx_original, 'duration'] = None
                        df_proc.loc[idx_original, 'horas_trabajadas'] = None
       
        print(f"✅ Procesamiento completado: {len(resultados)} turnos nocturnos procesados")
        return df_proc

    def analizar_asistencia_con_horarios_cache(self, df: pd.DataFrame, cache_horarios: Dict) -> pd.DataFrame:
        """
        Enriches the DataFrame with schedule and tardiness analysis using the schedule cache.
        """
        if df.empty:
            return df
        print("\n🔄 Iniciando análisis de horarios y retardos...")

        df["es_primera_quincena"] = df["dia"].apply(lambda x: x.day <= 15)

        df["hora_entrada_programada"] = None
        df["hora_salida_programada"] = None
        df["cruza_medianoche"] = False
        df["horas_esperadas"] = None

        def obtener_horario_fila(row):
            try:
                # SOLO 1 ARGUMENTO ahora
                horario = obtener_horario_empleado(str(row["employee"]))
               
                if horario:
                    horas_totales = horario.get("horas_totales", 8.0)
                    horas_totales_td = timedelta(hours=horas_totales)
                    horas_totales_str = str(horas_totales_td)
                   
                    if len(horas_totales_str.split(':')) == 2:
                        horas_totales_str += ":00"
                   
                    return pd.Series(
                        [
                            horario.get("hora_entrada"),
                            horario.get("hora_salida"),
                            horario.get("cruza_medianoche", False),
                            horas_totales_str,
                        ]
                    )
            except Exception as e:
                print(f"⚠️ Error obteniendo horario para {row['employee']}: {e}")
           
            return pd.Series(["08:00", "17:00", False, "08:00:00"])

        df[
            [
                "hora_entrada_programada",
                "hora_salida_programada",
                "cruza_medianoche",
                "horas_esperadas",
            ]
        ] = df.apply(obtener_horario_fila, axis=1, result_type="expand")

        print("   - Calculando retardos y puntualidad...")

        def analizar_retardo(row):
            if pd.isna(row.get("hora_entrada_programada")) or row.get("hora_entrada_programada") is None:
                return pd.Series(["Día no Laborable", 0])
           
            if pd.isna(row.get("checado_1")):
                if row.get("cruza_medianoche", False) and pd.notna(row.get("checado_2")):
                    return pd.Series(["Falta Entrada Nocturno", 0])
                return pd.Series(["Falta", 0])
           
            try:
                # Handle both HH:MM and HH:MM:SS formats
                hora_prog_str = row["hora_entrada_programada"]
                if len(hora_prog_str.split(':')) == 2:  # HH:MM format
                    hora_prog_str += ":00"
               
                hora_checada_str = row["checado_1"]
                if len(hora_checada_str.split(':')) == 2:  # HH:MM format
                    hora_checada_str += ":00"
                   
                hora_prog = datetime.strptime(hora_prog_str, "%H:%M:%S")
                hora_checada = datetime.strptime(hora_checada_str, "%H:%M:%S")

                if (
                    row.get("cruza_medianoche", False)
                    and hora_prog.hour >= 12
                    and hora_checada.hour < 12
                ):
                    hora_prog -= timedelta(days=1)

                diferencia = (hora_checada - hora_prog).total_seconds() / 60

                if not row.get("cruza_medianoche", False) and diferencia < -12 * 60:
                    diferencia += 24 * 60

                if diferencia <= TOLERANCIA_RETARDO_MINUTOS:
                    tipo = "A Tiempo"
                elif diferencia <= UMBRAL_FALTA_INJUSTIFICADA_MINUTOS:
                    tipo = "Retardo"
                else:
                    tipo = "Falta Injustificada"
                return pd.Series([tipo, int(diferencia)])
            except (ValueError, TypeError) as e:
                print(f"⚠️ Error calculando retardo para {row['employee']}: {e}")
                return pd.Series(["Falta", 0])

        df[["tipo_retardo", "minutos_tarde"]] = df.apply(
            analizar_retardo, axis=1, result_type="expand"
        )

        df = df.sort_values(by=["employee", "dia"]).reset_index(drop=True)
        df["es_retardo_acumulable"] = (df["tipo_retardo"] == "Retardo").astype(int)
        df["es_falta"] = (
            df["tipo_retardo"].isin(["Falta", "Falta Injustificada"])
        ).astype(int)
        df["retardos_acumulados"] = df.groupby("employee")[
            "es_retardo_acumulable"
        ].cumsum()

        df["descuento_por_3_retardos"] = df.apply(
            lambda row: (
                "Sí (3er retardo)"
                if row["es_retardo_acumulable"]
                and row["retardos_acumulados"] > 0
                and row["retardos_acumulados"] % 3 == 0
                else "No"
            ),
            axis=1,
        )

        print("   - Detectando salidas anticipadas...")

        # Function to detect early departures
        def detectar_salida_anticipada(row):
            # Only apply if scheduled exit time exists and at least one check-in
            if pd.isna(row.get("hora_salida_programada")) or pd.isna(row.get("checado_1")):
                return False

            # Get the last check-in of the day (the one with the highest value)
            checadas_dia = []
            for i in range(1, 10):  # Search up to checado_9
                col_checado = f"checado_{i}"
                if col_checado in row and pd.notna(row[col_checado]):
                    checadas_dia.append(row[col_checado])

            # If there's only one check-in, don't consider early departure
            if len(checadas_dia) <= 1:
                return False

            # Get the last check-in (convert to datetime to compare correctly)
            try:
                checadas_datetime = [
                    datetime.strptime(checada, "%H:%M:%S") for checada in checadas_dia
                ]

                # For shifts that cross midnight, we need to adjust hours
                if row.get("cruza_medianoche", False):
                    # In night shifts, we need to compare chronologically
                    checadas_ajustadas = []
                    for dt in checadas_datetime:
                        if dt.hour < 12:  # If before noon (00:00-11:59), add 24 hours
                            dt_ajustado = dt + timedelta(hours=24)
                            checadas_ajustadas.append(dt_ajustado)
                        else:
                            checadas_ajustadas.append(dt)
                    ultima_checada_dt = max(checadas_ajustadas)
                    # Convert back to original format
                    ultima_checada = ultima_checada_dt.strftime("%H:%M:%S")
                else:
                    ultima_checada = max(checadas_datetime).strftime("%H:%M:%S")
            except (ValueError, TypeError):
                return False

            try:
                # Parse scheduled exit time
                hora_salida_prog_str = row["hora_salida_programada"]
                if len(hora_salida_prog_str.split(':')) == 2:  # HH:MM format
                    hora_salida_prog_str += ":00"
                   
                hora_salida_prog = datetime.strptime(hora_salida_prog_str, "%H:%M:%S")
                hora_ultima_checada = datetime.strptime(ultima_checada, "%H:%M:%S")

                # Handle shifts that cross midnight
                if row.get("cruza_medianoche", False):
                    # For shifts that cross midnight, scheduled exit time is on the next day
                    # We don't need to adjust anything here since we're only comparing hours
                    pass

                # Calculate difference in minutes
                diferencia = (
                    hora_salida_prog - hora_ultima_checada
                ).total_seconds() / 60

                # Handle midnight cases
                if diferencia < -12 * 60:  # More than 12 hours before
                    diferencia += 24 * 60
                elif diferencia > 12 * 60:  # More than 12 hours after
                    diferencia -= 24 * 60

                # Consider early departure if last check-in is before scheduled exit time
                # minus tolerance margin
                return diferencia > TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS

            except (ValueError, TypeError):
                return False

        # Apply early departure detection
        df["salida_anticipada"] = df.apply(detectar_salida_anticipada, axis=1)

        print("✅ Análisis completado.")
        return df

    def ajustar_horas_esperadas_con_permisos(
        self, df: pd.DataFrame, permisos_dict: Dict, cache_horarios: Dict
    ) -> pd.DataFrame:
        """
        Adjusts expected hours in the DataFrame considering approved leaves.
        Properly handles half-day leaves.
        """
        if df.empty:
            return df

        print("📊 Ajustando horas esperadas considerando permisos aprobados...")

        df["tiene_permiso"] = False
        df["tipo_permiso"] = None
        df["es_permiso_sin_goce"] = False
        df["es_permiso_medio_dia"] = False
        df["horas_esperadas_originales"] = df["horas_esperadas"].copy()
        df["horas_descontadas_permiso"] = "00:00:00"

        permisos_con_descuento = 0
        permisos_sin_goce = 0
        permisos_medio_dia = 0

        for index, row in df.iterrows():
            employee_code = str(row["employee"])
            fecha = row["dia"]

            if employee_code in permisos_dict and fecha in permisos_dict[employee_code]:
                permiso_info = permisos_dict[employee_code][fecha]
                leave_type_normalized = permiso_info.get("leave_type_normalized", "")
                is_half_day = permiso_info.get("is_half_day", False)

                df.at[index, "tiene_permiso"] = True
                df.at[index, "tipo_permiso"] = permiso_info["leave_type"]
                df.at[index, "es_permiso_medio_dia"] = is_half_day

                accion = POLITICA_PERMISOS.get(leave_type_normalized, "ajustar_a_cero")

                horas_esperadas_orig = row["horas_esperadas"]

                if (
                    pd.notna(horas_esperadas_orig)
                    and horas_esperadas_orig != "00:00:00"
                ):
                    if accion == "no_ajustar":
                        df.at[index, "es_permiso_sin_goce"] = True
                        permisos_sin_goce += 1
                    elif accion == "ajustar_a_cero":
                        if is_half_day:
                            # For half-day leaves, deduct only half the hours
                            try:
                                # Convert expected hours to timedelta
                                horas_td = pd.to_timedelta(horas_esperadas_orig)
                                # Calculate half
                                mitad_horas = horas_td / 2
                                # Convert back to string
                                mitad_horas_str = str(mitad_horas).split()[
                                    -1
                                ]  # Get only HH:MM:SS

                                # Adjust expected hours (subtract half)
                                horas_ajustadas = horas_td - mitad_horas
                                horas_ajustadas_str = str(horas_ajustadas).split()[-1]

                                df.at[index, "horas_esperadas"] = horas_ajustadas_str
                                df.at[index, "horas_descontadas_permiso"] = (
                                    mitad_horas_str
                                )
                                permisos_medio_dia += 1
                            except (ValueError, TypeError):
                                # If there's an error in calculation, treat as full day
                                df.at[index, "horas_esperadas"] = "00:00:00"
                                df.at[index, "horas_descontadas_permiso"] = (
                                    horas_esperadas_orig
                                )
                                permisos_con_descuento += 1
                        else:
                            # Full day leave
                            df.at[index, "horas_esperadas"] = "00:00:00"
                            df.at[index, "horas_descontadas_permiso"] = (
                                horas_esperadas_orig
                            )
                            permisos_con_descuento += 1

        empleados_con_permisos = df[df["tiene_permiso"]]["employee"].nunique()
        dias_con_permisos = df["tiene_permiso"].sum()

        print("✅ Ajuste completado:")
        print(f"   - {empleados_con_permisos} empleados con permisos")
        print(f"   - {dias_con_permisos} días con permisos")
        print(
            f"   - {permisos_con_descuento} permisos con horas descontadas (día completo)"
        )
        print(f"   - {permisos_medio_dia} permisos de medio día")
        print(f"   - {permisos_sin_goce} permisos sin goce (sin descuento)")

        return df

    def aplicar_regla_perdon_retardos(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies the tardiness forgiveness rule when an employee fulfills their shift hours.

        If an employee worked the corresponding hours of their shift or more, that day should NOT
        count as tardiness, even if they arrived late.
        """
        if df.empty:
            return df

        print("🔄 Applying tardiness forgiveness rule for hour fulfillment...")

        # Use Timedelta columns if they exist, otherwise convert from strings
        if "duration_td" in df.columns:
            df["horas_trabajadas_td"] = df["duration_td"].fillna(pd.Timedelta(0))
        else:
            df["horas_trabajadas_td"] = df["horas_trabajadas"].apply(safe_timedelta)

        df["horas_esperadas_td"] = df["horas_esperadas"].apply(safe_timedelta)

        # Calculate if shift hours were fulfilled
        df["cumplio_horas_turno"] = (
            df["horas_trabajadas_td"] >= df["horas_esperadas_td"]
        )

        # Save original values before applying forgiveness
        df["tipo_retardo_original"] = df["tipo_retardo"].copy()
        df["minutos_tarde_original"] = df["minutos_tarde"].copy()
        df["retardo_perdonado"] = False

        # Apply forgiveness to tardiness
        mask_retardo_perdonable = (df["tipo_retardo"] == "Retardo") & (
            df["cumplio_horas_turno"]
        )

        if mask_retardo_perdonable.any():
            df.loc[mask_retardo_perdonable, "retardo_perdonado"] = True
            df.loc[mask_retardo_perdonable, "tipo_retardo"] = "A Tiempo (Cumplió Horas)"
            df.loc[mask_retardo_perdonable, "minutos_tarde"] = 0
            retardos_perdonados = mask_retardo_perdonable.sum()
            print(f"   - {retardos_perdonados} tardiness forgiven for fulfilling hours")

        # Apply forgiveness to unjustified absences (optional)
        if PERDONAR_TAMBIEN_FALTA_INJUSTIFICADA:
            mask_falta_perdonable = (df["tipo_retardo"] == "Falta Injustificada") & (
                df["cumplio_horas_turno"]
            )

            if mask_falta_perdonable.any():
                df.loc[mask_falta_perdonable, "retardo_perdonado"] = True
                df.loc[mask_falta_perdonable, "tipo_retardo"] = (
                    "A Tiempo (Cumplió Horas)"
                )
                df.loc[mask_falta_perdonable, "minutos_tarde"] = 0
                faltas_perdonadas = mask_falta_perdonable.sum()
                print(
                    f"   - {faltas_perdonadas} unjustified absences forgiven for fulfilling hours"
                )

        # Recalculate derived columns
        df["es_retardo_acumulable"] = (df["tipo_retardo"] == "Retardo").astype(int)
        df["es_falta"] = (
            df["tipo_retardo"].isin(["Falta", "Falta Injustificada"])
        ).astype(int)

        # Recalculate accumulated tardiness by employee
        df["retardos_acumulados"] = df.groupby("employee")[
            "es_retardo_acumulable"
        ].cumsum()

        # Recalculate discount for 3 tardiness
        df["descuento_por_3_retardos"] = df.apply(
            lambda row: (
                "Sí (3er retardo)"
                if row["es_retardo_acumulable"]
                and row["retardos_acumulados"] > 0
                and row["retardos_acumulados"] % 3 == 0
                else "No"
            ),
            axis=1,
        )

        total_perdonados = df["retardo_perdonado"].sum()
        if total_perdonados > 0:
            print(
                f"✅ Forgiveness applied to {total_perdonados} days for hour fulfillment"
            )
        else:
            print("✅ No days found eligible for forgiveness")

        return df

    def clasificar_faltas_con_permisos(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Updates absence classification considering approved leaves.
        """
        if df.empty:
            return df

        print("📋 Reclassifying absences considering approved leaves...")

        df["tipo_falta_ajustada"] = df["tipo_retardo"].copy()
        df["falta_justificada"] = False

        mask_permiso_y_falta = (df["tiene_permiso"]) & (
            df["tipo_retardo"].isin(["Falta", "Falta Injustificada"])
        )

        if mask_permiso_y_falta.any():
            df.loc[mask_permiso_y_falta, "tipo_falta_ajustada"] = "Falta Justificada"
            df.loc[mask_permiso_y_falta, "falta_justificada"] = True
            faltas_justificadas = mask_permiso_y_falta.sum()
            print(f"✅ {faltas_justificadas} absences justified with approved leaves.")
        else:
            print("✅ No absences found to justify with leaves.")

        # Calculate es_falta_ajustada in both cases
        df["es_falta_ajustada"] = (
            df["tipo_falta_ajustada"].isin(["Falta", "Falta Injustificada"])
        ).astype(int)

        return df

    def marcar_dias_no_contratado(self, df: pd.DataFrame, joining_dates_dict: Dict) -> pd.DataFrame:
        """
        Marks days before an employee's joining date as 'No Contratado'.
        This prevents these days from being counted as absences.
        """
        if df.empty or not joining_dates_dict:
            return df

        print("📝 Marcando días previos a la contratación como 'No Contratado'...")

        # Map joining dates to a temporary column
        df['fecha_contratacion'] = df['employee'].astype(str).map(joining_dates_dict)

        # Create a boolean mask for rows where the day is before the joining date
        # pd.NaT will be correctly handled in comparisons (evaluating to False)
        mask = pd.to_datetime(df['dia']) < pd.to_datetime(df['fecha_contratacion'])

        # Count how many employees and days will be affected
        affected_employees = df[mask]['employee'].nunique() if mask.any() else 0
        affected_days = mask.sum()
       
        if affected_days > 0:
            print(f"   - Se marcarán {affected_days} días de {affected_employees} empleados como 'No Contratado'")
        else:
            print("   - No se encontraron días previos a contratación para marcar")

        if mask.any():
            update_values = {
                "tiene_permiso": True,
                "tipo_permiso": "No Contratado",
                "horas_esperadas": "00:00:00",
                "horas_esperadas_originales": "00:00:00",
                "tipo_retardo": "No Contratado",
                "tipo_falta_ajustada": "No Contratado",
                "minutos_tarde": 0,
                "es_falta": 0,
                "es_falta_ajustada": 0,
                "falta_justificada": False,
                "retardo_perdonado": False,
                "salida_anticipada": False,
            }

            for col, value in update_values.items():
                if col in df.columns:
                    df.loc[mask, col] = value

        # Clean up the temporary column
        df.drop(columns=['fecha_contratacion'], inplace=True)

        return df

# PEGA ESTE CÓDIGO CORREGIDO EN SU LUGAR
# DENTRO de la clase AttendanceProcessor en services.py

    def _contar_checadas_validas(self, row):
        """Cuenta el número de checadas no nulas en una fila."""
        checadas = 0
        for i in range(1, 10): # Revisa de checado_1 a checado_9
            if f'checado_{i}' in row and pd.notna(row[f'checado_{i}']):
                checadas += 1
        return checadas
   
    def calcular_totales_por_empleado(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula los totales para todo el período por cada empleado,
        garantizando UNA SOLA fila de resumen por empleado.
        """
        try:
            print(f"✅ Iniciando resumen final. {len(df)} filas de detalle recibidas.")
           
            if df.empty:
                print("❌ DataFrame detallado está vacío. No se puede generar resumen.")
                return pd.DataFrame()

            df_work = df.copy()

            # --- Asegurar columnas necesarias para el cálculo ---
            if 'Nombre' not in df_work.columns and 'employee_name' in df_work.columns:
                df_work['Nombre'] = df_work['employee_name']
           
            # Convertir columnas de tiempo a timedelta para poder sumarlas
            columnas_tiempo = ['horas_trabajadas', 'horas_esperadas', 'horas_descontadas_permiso', 'horas_descanso']
            for col in columnas_tiempo:
                if col in df_work.columns:
                    df_work[f'{col}_td'] = pd.to_timedelta(df_work[col], errors='coerce').fillna(pd.Timedelta(0))
                else:
                    df_work[f'{col}_td'] = pd.Timedelta(0)

            # Asegurar que las columnas numéricas existan para evitar errores
            columnas_numericas = ['es_retardo_acumulable', 'es_falta', 'salida_anticipada', 'falta_justificada', 'episodios_ausencia']
            for col in columnas_numericas:
                if col not in df_work.columns:
                    df_work[col] = 0

            # --- NUEVA LÓGICA PARA EPISODIOS DE AUSENCIA ---
            df_work['num_checadas'] = df_work.apply(self._contar_checadas_validas, axis=1)
            # Un episodio de ausencia = 1 par de checadas intermedias (salida/entrada). Requiere al menos 4 checadas en el día.
            # Fórmula: (Num Checadas - 2) / 2
            df_work['episodios_ausencia_diarios'] = df_work['num_checadas'].apply(
                lambda x: max(0, (x - 2) // 2) if x >= 4 else 0
            )
            # --- FIN DE LA NUEVA LÓGICA ---

            # --- LA CORRECCIÓN CLAVE: Agrupar solo por empleado y nombre ---
            group_cols = ['employee', 'Nombre']
            print(f"🔍 Agrupando por: {group_cols} para el período completo...")

            df_resumen = df_work.groupby(group_cols).agg(
                total_horas_trabajadas=('horas_trabajadas_td', 'sum'),
                total_horas_esperadas=('horas_esperadas_td', 'sum'),
                total_horas_descontadas_permiso=('horas_descontadas_permiso_td', 'sum'),
                total_horas_descanso=('horas_descanso_td', 'sum'),
                total_retardos=('es_retardo_acumulable', 'sum'),
                faltas_del_periodo=('es_falta', 'sum'),
                faltas_justificadas=('falta_justificada', 'sum'),
                total_salidas_anticipadas=('salida_anticipada', 'sum'),
                episodios_ausencia=('episodios_ausencia_diarios', 'sum')
            ).reset_index()

            # --- Cálculos Finales ---
            df_resumen['total_horas'] = df_resumen['total_horas_esperadas'] - df_resumen['total_horas_descontadas_permiso']
            df_resumen['total_faltas'] = df_resumen['faltas_del_periodo']
            df_resumen['diferencia_td'] = df_resumen['total_horas_trabajadas'] - df_resumen['total_horas']

            # --- Formateo final a texto HH:MM:SS ---
            columnas_a_formatear = ['total_horas_trabajadas', 'total_horas_esperadas', 'total_horas_descontadas_permiso', 'total_horas_descanso', 'total_horas']
            for col in columnas_a_formatear:
                df_resumen[col] = df_resumen[col].apply(td_to_str)
               
            df_resumen['diferencia_HHMMSS'] = df_resumen['diferencia_td'].apply(td_to_str)
           
            print(f"✅ Resumen final generado con {len(df_resumen)} filas únicas de empleados.")
            return df_resumen

        except Exception as e:
            print(f"❌ Error crítico en calcular_totales_por_empleado: {str(e)}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def _calcular_horas_descontadas_simple(self, df_empleado: pd.DataFrame) -> str:
        """Calcula horas descontadas de manera simple - MEJORADO"""
        try:
            print(f"🔍 Buscando columna horas_descontadas_permiso...")
           
            # Verificar si la columna existe y tiene datos
            if 'horas_descontadas_permiso' in df_empleado.columns:
                print(f"✅ Columna encontrada. Valores: {df_empleado['horas_descontadas_permiso'].unique()}")
               
                total_segundos = 0
                for valor in df_empleado['horas_descontadas_permiso']:
                    if pd.notna(valor) and str(valor).strip() not in ["", "00:00:00", "NaT"]:
                        try:
                            if isinstance(valor, str):
                                # Limpiar y procesar el valor
                                valor_limpio = str(valor).strip()
                                partes = valor_limpio.split(':')
                               
                                if len(partes) >= 2:
                                    h = int(partes[0]) if partes[0] else 0
                                    m = int(partes[1]) if partes[1] else 0
                                    s = int(partes[2]) if len(partes) > 2 and partes[2] else 0
                                   
                                    segundos_dia = h * 3600 + m * 60 + s
                                    total_segundos += segundos_dia
                                    print(f"   - Día: {valor} -> {segundos_dia} segundos")
                        except Exception as e:
                            print(f"   ⚠️ Error procesando valor {valor}: {e}")
                            continue
               
                horas = total_segundos // 3600
                minutos = (total_segundos % 3600) // 60
                segundos = total_segundos % 60
                resultado = f"{horas:02d}:{minutos:02d}:{segundos:02d}"
                print(f"✅ total_horas_descontadas_permiso calculado: {resultado}")
                return resultado
            else:
                print("❌ Columna 'horas_descontadas_permiso' no encontrada")
               
        except Exception as e:
            print(f"❌ Error en _calcular_horas_descontadas_simple: {e}")
       
        return "00:00:00"

    def _calcular_horas_descanso_simple(self, df_empleado: pd.DataFrame) -> str:
        """Calcula horas de descanso de manera simple - MEJORADO"""
        try:
            print(f"🔍 Buscando columna horas_descanso...")
           
            # PRIMERO: Buscar en la columna específica
            if 'horas_descanso' in df_empleado.columns:
                print(f"✅ Columna horas_descanso encontrada. Valores: {df_empleado['horas_descanso'].unique()}")
               
                total_segundos = 0
                for valor in df_empleado['horas_descanso']:
                    if pd.notna(valor) and str(valor).strip() not in ["", "00:00:00", "NaT"]:
                        try:
                            if isinstance(valor, str):
                                valor_limpio = str(valor).strip()
                                partes = valor_limpio.split(':')
                               
                                if len(partes) >= 2:
                                    h = int(partes[0]) if partes[0] else 0
                                    m = int(partes[1]) if partes[1] else 0
                                    s = int(partes[2]) if len(partes) > 2 and partes[2] else 0
                                   
                                    segundos_dia = h * 3600 + m * 60 + s
                                    total_segundos += segundos_dia
                        except:
                            continue
               
                horas = total_segundos // 3600
                minutos = (total_segundos % 3600) // 60
                segundos = total_segundos % 60
                resultado = f"{horas:02d}:{minutos:02d}:{segundos:02d}"
                print(f"✅ total_horas_descanso calculado: {resultado}")
                return resultado
            else:
                print("❌ Columna 'horas_descanso' no encontrada")
               
        except Exception as e:
            print(f"❌ Error en _calcular_horas_descanso_simple: {e}")
       
        return "00:00:00"

    def _calcular_total_horas_simple(self, df_empleado: pd.DataFrame) -> str:
        """Calcula total horas de manera simple - MEJORADO"""
        try:
            print(f"🔍 Calculando total_horas desde columna horas_trabajadas...")
           
            if 'horas_trabajadas' in df_empleado.columns:
                print(f"✅ Columna horas_trabajadas encontrada")
               
                total_segundos = 0
                dias_con_horas = 0
               
                for valor in df_empleado['horas_trabajadas']:
                    if pd.notna(valor) and str(valor).strip() not in ["", "00:00:00", "NaT"]:
                        try:
                            if isinstance(valor, str):
                                valor_limpio = str(valor).strip()
                                partes = valor_limpio.split(':')
                               
                                if len(partes) >= 2:
                                    h = int(partes[0]) if partes[0] else 0
                                    m = int(partes[1]) if partes[1] else 0
                                    s = int(partes[2]) if len(partes) > 2 and partes[2] else 0
                                   
                                    segundos_dia = h * 3600 + m * 60 + s
                                    total_segundos += segundos_dia
                                    dias_con_horas += 1
                        except:
                            continue
               
                horas = total_segundos // 3600
                minutos = (total_segundos % 3600) // 60
                segundos = total_segundos % 60
                resultado = f"{horas:02d}:{minutos:02d}:{segundos:02d}"
                print(f"✅ total_horas calculado: {resultado} (de {dias_con_horas} días)")
                return resultado
               
        except Exception as e:
            print(f"❌ Error en _calcular_total_horas_simple: {e}")
       
        return "00:00:00"

    def _calcular_faltas_detalladas(self, df_empleado: pd.DataFrame) -> dict:
        """Calcula faltas detalladas - MEJORADO"""
        try:
            print(f"🔍 Calculando faltas desde columna tipo_retardo...")
           
            if 'tipo_retardo' in df_empleado.columns:
                print(f"✅ Columna tipo_retardo encontrada. Valores: {df_empleado['tipo_retardo'].unique()}")
               
                faltas_normales = (df_empleado['tipo_retardo'] == 'Falta').sum()
                faltas_injustificadas = (df_empleado['tipo_retardo'] == 'Falta Injustificada').sum()
                faltas_totales = faltas_normales + faltas_injustificadas
               
                # Por ahora, asumimos que no hay faltas justificadas
                faltas_justificadas = 0
                faltas_periodo = faltas_totales - faltas_justificadas
               
                resultado = {
                    "faltas_del_periodo": str(int(faltas_periodo)),
                    "faltas_justificadas": str(int(faltas_justificadas)),
                    "total_faltas": str(int(faltas_totales))
                }
               
                print(f"✅ Faltas calculadas: {resultado}")
                return resultado
            else:
                print("❌ Columna 'tipo_retardo' no encontrada")
               
        except Exception as e:
            print(f"❌ Error en _calcular_faltas_detalladas: {e}")
       
        return {
            "faltas_del_periodo": "0",
            "faltas_justificadas": "0",
            "total_faltas": "0"
        }

    def _calcular_episodios_ausencia_simple(self, df_empleado: pd.DataFrame) -> str:
        """Calcula episodios de ausencia de manera simple - MEJORADO"""
        try:
            print(f"🔍 Calculando episodios_ausencia...")
           
            episodios = 0
            for index, fila in df_empleado.iterrows():
                checadas_extra = 0
                for i in range(3, 10):  # checado_3 a checado_9
                    columna = f'checado_{i}'
                    if columna in fila and pd.notna(fila[columna]) and str(fila[columna]).strip() not in ["", "---", "NaT"]:
                        checadas_extra += 1
               
                if checadas_extra > 0:
                    print(f"   - Día {index}: {checadas_extra} checadas extra")
                    episodios += checadas_extra
           
            resultado = str(int(episodios))
            print(f"✅ episodios_ausencia calculado: {resultado}")
            return resultado
           
        except Exception as e:
            print(f"❌ Error en _calcular_episodios_ausencia_simple: {e}")
            return "0"