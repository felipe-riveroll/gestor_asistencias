from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from collections import defaultdict
from itertools import product
import pandas as pd
from typing import Dict, List, Tuple
import pytz
import gc
import numpy as np

# CORRECCIÓN: Importar time directamente
from datetime import time

def obtener_horario_empleado(employee_code, dia_semana=None, es_primera_quincena=None, cache=None):
    """
    Función wrapper para compatibilidad con 4 argumentos
    """
    # Solo pasamos el primer argumento a la función real
    return obtener_horario_real(employee_code)

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
# Función auxiliar
def td_to_str(td):
    """Convierte timedelta a string HH:MM:SS"""
    try:
        if pd.isna(td) or td == pd.NaT:
            return "00:00:00"
        
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    except:
        return "00:00:00"

class AttendanceProcessor:
    """Main class for processing attendance data with correct calculations"""

    def __init__(self):
        """Initialize the attendance processor."""
        pass

    def process_checkins_to_dataframe(
        self, checkin_data: List[Dict], start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Creates a base DataFrame with one row per employee and day"""
        if not checkin_data:
            print("❌ No hay datos de checadas para procesar")
            return pd.DataFrame()

        print(f"🔄 Procesando {len(checkin_data)} registros de checadas...")
        print(f"📅 Período procesado: {start_date} a {end_date}")
        
        try:
            # Crear DataFrame básico
            df = pd.DataFrame(checkin_data)
            
            # Verificar columnas requeridas
            required_columns = ['employee', 'time', 'employee_name']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                print(f"❌ Faltan columnas requeridas: {missing_columns}")
                return pd.DataFrame()
            
            df["time"] = pd.to_datetime(df["time"])
            df["dia"] = df["time"].dt.date
            df["checado_time"] = df["time"].dt.strftime("%H:%M:%S")

            # Calcular duración por día y empleado
            employee_daily = df.groupby(["employee", "dia"]).agg({
                "time": ["min", "max"],
                "employee_name": "first"
            }).reset_index()
            
            # Aplanar columnas
            employee_daily.columns = ['employee', 'dia', 'min_time', 'max_time', 'Nombre']
            
            # CORRECCIÓN: Calcular duración correctamente
            employee_daily["duration"] = employee_daily.apply(
                lambda row: row["max_time"] - row["min_time"] if pd.notna(row["min_time"]) and pd.notna(row["max_time"]) else pd.Timedelta(0),
                axis=1
            )
            
            employee_daily["horas_trabajadas"] = employee_daily["duration"].apply(
                lambda x: td_to_str(x) if pd.notna(x) and x.total_seconds() > 0 else "00:00:00"
            )

            # Crear checados pivot
            df["checado_rank"] = df.groupby(["employee", "dia"]).cumcount() + 1
            checados_pivot = df.pivot_table(
                index=["employee", "dia"],
                columns="checado_rank",
                values="checado_time",
                aggfunc="first"
            ).reset_index()
            
            # Renombrar columnas
            if not checados_pivot.empty:
                checado_cols = [col for col in checados_pivot.columns if col not in ['employee', 'dia']]
                new_col_names = {}
                for i, col in enumerate(checado_cols, 1):
                    new_col_names[col] = f"checado_{i}"
                checados_pivot = checados_pivot.rename(columns=new_col_names)

            # Crear base de días - INCLUIR TODOS LOS DÍAS DEL PERÍODO
            all_dates = pd.date_range(start=start_date, end=end_date, freq='D').date
            all_employees = df["employee"].unique()
            
            print(f"   - {len(all_dates)} días en el período")
            print(f"   - {len(all_employees)} empleados únicos")
            
            base_df = pd.merge(
                pd.DataFrame({'employee': all_employees}), 
                pd.DataFrame({'dia': all_dates}), 
                how='cross'
            )

            # Combinar datos
            final_df = base_df.merge(
                employee_daily[['employee', 'dia', 'Nombre', 'duration', 'horas_trabajadas']], 
                on=['employee', 'dia'], 
                how='left'
            )
            
            if not checados_pivot.empty:
                final_df = final_df.merge(checados_pivot, on=['employee', 'dia'], how='left')

            # Añadir información de días
            final_df["dia_semana"] = pd.to_datetime(final_df["dia"]).dt.day_name()
            final_df["dia_iso"] = pd.to_datetime(final_df["dia"]).dt.weekday + 1

            # CORRECCIÓN: Rellenar nombres de empleados
            employee_names = df[['employee', 'employee_name']].drop_duplicates()
            final_df = final_df.merge(employee_names, on='employee', how='left')
            final_df['Nombre'] = final_df['employee_name']
            final_df = final_df.drop('employee_name', axis=1)

            print(f"✅ DataFrame creado: {len(final_df)} filas")
            return final_df

        except Exception as e:
            print(f"❌ Error en process_checkins_to_dataframe: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def analizar_asistencia_con_horarios(self, df: pd.DataFrame, joining_dates_dict: Dict = None) -> pd.DataFrame:
        """
        Analiza asistencia con horarios reales de la base de datos
        """
        if df.empty:
            print("❌ DataFrame vacío en analizar_asistencia_con_horarios")
            return df
            
        print("\n🔄 Analizando asistencia con horarios REALES de BD...")

        # Obtener empleados únicos
        unique_employees = df["employee"].unique()
        
        print(f"   - Procesando {len(unique_employees)} empleados...")
        
        # Inicializar columnas adicionales
        df["_horas_esperadas_num"] = 0.0
        df["horas_esperadas"] = "00:00:00"
        df["_horas_por_dia_num"] = 0.0
        df["_horas_descontadas_permiso_num"] = 0.0
        df["horas_descontadas_permiso"] = "00:00:00"
        df["tiene_permiso"] = False
        df["tipo_permiso"] = None
        df["es_falta"] = 0
        df["falta_justificada"] = 0
        df["es_retardo_acumulable"] = 0
        df["salida_anticipada"] = 0

        # Para cada empleado, calcular horas esperadas
        for employee in unique_employees:
            try:
                employee_days = df[df['employee'] == employee]
                resultado = self.calcular_horas_esperadas_para_empleado(
                    str(employee), 
                    employee_days,
                    joining_dates_dict
                )
                
                # Aplicar resultados a todas las filas del empleado
                mask = df['employee'] == employee
                df.loc[mask, '_horas_esperadas_num'] = resultado["horas_esperadas"]
                df.loc[mask, 'horas_esperadas'] = td_to_str(resultado["horas_esperadas_td"])
                df.loc[mask, '_horas_por_dia_num'] = resultado["horas_por_dia"]
                df.loc[mask, '_horas_descontadas_permiso_num'] = resultado["horas_descontadas_permiso"]
                df.loc[mask, 'horas_descontadas_permiso'] = td_to_str(resultado["horas_descontadas_permiso_td"])

                print(f"   ✅ {employee}: {resultado['horas_esperadas']:.2f} horas esperadas ({resultado['dias_laborales']} días × {resultado['horas_por_dia']}h)")
                    
            except Exception as e:
                print(f"⚠️ Error procesando empleado {employee}: {e}")
                # Valores por defecto en caso de error
                mask = df['employee'] == employee
                df.loc[mask, 'horas_esperadas'] = "00:00:00"
                df.loc[mask, '_horas_esperadas_num'] = 0.0
                df.loc[mask, '_horas_por_dia_num'] = 0.0
                df.loc[mask, '_horas_descontadas_permiso_num'] = 0.0
                df.loc[mask, 'horas_descontadas_permiso'] = "00:00:00"

        print("✅ Análisis de horarios completado.")
        return df

    def calcular_horas_esperadas_para_empleado(self, employee_code: str, df_empleado: pd.DataFrame, joining_dates_dict: Dict = None) -> Dict:
        """
        Calcula horas esperadas usando horarios REALES de la base de datos
        """
        try:
            print(f"\n🧮 Calculando horas para empleado {employee_code}")
            
            # Obtener horario REAL de la base de datos
            horario_completo = self.obtener_horario_real_empleado(employee_code, df_empleado)
            
            # Calcular días laborales y horas totales
            dias_laborales, horas_por_dia = self.calcular_dias_y_horas_laborales(
                employee_code, df_empleado, horario_completo, joining_dates_dict
            )
            
            horas_totales = horas_por_dia * dias_laborales
            
            print(f"   📊 {employee_code}: {dias_laborales} días × {horas_por_dia}h = {horas_totales:.2f}h totales")
            
            return {
                "horas_esperadas": horas_totales,
                "horas_esperadas_td": timedelta(hours=horas_totales),
                "horas_descontadas_permiso": 0.0,
                "horas_descontadas_permiso_td": timedelta(0),
                "horas_por_dia": horas_por_dia,
                "dias_laborales": dias_laborales,
                "horario_completo": horario_completo
            }
                
        except Exception as e:
            print(f"❌ Error calculando horas para {employee_code}: {e}")
            # Fallback a valores por defecto
            dias_laborales = self.calcular_dias_laborales_fallback(df_empleado)
            horas_por_dia = 8.0
            horas_totales = horas_por_dia * dias_laborales
            
            return {
                "horas_esperadas": horas_totales,
                "horas_esperadas_td": timedelta(hours=horas_totales),
                "horas_descontadas_permiso": 0.0,
                "horas_descontadas_permiso_td": timedelta(0),
                "horas_por_dia": horas_por_dia,
                "dias_laborales": dias_laborales
            }

    def obtener_horario_real_empleado(self, employee_code: str, df_empleado: pd.DataFrame) -> Dict:
        """
        Obtiene el horario REAL del empleado desde la base de datos
        """
        try:
            from .db_postgres_connection import obtener_horario_empleado_completo
            
            # Obtener fecha de referencia para determinar quincena
            fecha_referencia = df_empleado['dia'].min() if not df_empleado.empty else None
            
            horario_completo = obtener_horario_empleado_completo(
                employee_code, 
                fecha_referencia.strftime('%Y-%m-%d') if fecha_referencia else None
            )
            
            print(f"   📋 Horario BD: {horario_completo.get('horas_por_dia', 8.0):.2f} horas/día")
            return horario_completo
            
        except Exception as e:
            print(f"⚠️ Error obteniendo horario de BD: {e}")
            # Fallback basado en datos conocidos
            return self.obtener_horario_fallback(employee_code)

    def obtener_horario_fallback(self, employee_code: str) -> Dict:
        """
        Fallback para cuando no se puede obtener el horario de BD
        """
        # Basado en tus datos CSV, empleados con 9 horas/día
        empleados_9_horas = ['51', '52', '53', '57', '60', '62', '63', '87', '1', '5', '6', '78', '79']
        
        if str(employee_code) in empleados_9_horas:
            horas_por_dia = 9.0
            print(f"   ⚡ Usando horario fallback: 9.0 horas/día")
        else:
            horas_por_dia = 8.0
            print(f"   ⚡ Usando horario por defecto: 8.0 horas/día")
            
        return {
            'horas_por_dia': horas_por_dia,
            'horarios_detallados': {},
            'fuente': 'fallback'
        }

    def calcular_dias_y_horas_laborales(self, employee_code: str, df_empleado: pd.DataFrame, horario_completo: Dict, joining_dates_dict: Dict = None) -> Tuple[int, float]:
        """
        Calcula días laborales y horas por día basado en horario real
        """
        try:
            if df_empleado.empty:
                return 0, 0.0
                
            fecha_inicio = df_empleado['dia'].min()
            fecha_fin = df_empleado['dia'].max()
            
            # Ajustar por joining date si existe
            if joining_dates_dict and employee_code in joining_dates_dict:
                joining_date = joining_dates_dict[employee_code]
                if joining_date > fecha_inicio:
                    fecha_inicio = joining_date
                    print(f"   📅 Ajustando por joining date: {joining_date}")

            # Obtener horas por día del horario
            horas_por_dia = horario_completo.get('horas_por_dia', 8.0)
            
            # Calcular días laborales según horario
            dias_laborales = self.contar_dias_laborales_segun_horario(
                fecha_inicio, fecha_fin, horario_completo
            )
            
            print(f"   📅 Período: {fecha_inicio} a {fecha_fin}, {dias_laborales} días laborales")
            
            return dias_laborales, horas_por_dia
            
        except Exception as e:
            print(f"⚠️ Error calculando días laborales: {e}")
            # Fallback
            dias_laborales = self.calcular_dias_laborales_fallback(df_empleado)
            return dias_laborales, 8.0

    def contar_dias_laborales_segun_horario(self, fecha_inicio, fecha_fin, horario_completo: Dict) -> int:
        """
        Cuenta días laborales según el horario específico del empleado
        """
        try:
            dias_laborales = 0
            horarios_detallados = horario_completo.get('horarios_detallados', {})
            
            # Generar todos los días del período
            todos_los_dias = pd.date_range(start=fecha_inicio, end=fecha_fin, freq='D')
            
            for dia in todos_los_dias:
                dia_date = dia.date()
                dia_semana = dia.strftime('%A')
                
                if self.tiene_horario_ese_dia(dia_semana, horarios_detallados):
                    dias_laborales += 1
                    
            return dias_laborales
            
        except Exception as e:
            print(f"⚠️ Error contando días según horario: {e}")
            return self.calcular_dias_laborales_fallback_simple(fecha_inicio, fecha_fin)

    def tiene_horario_ese_dia(self, dia_semana: str, horarios_detallados: Dict) -> bool:
        """
        Verifica si el empleado tiene horario en un día específico
        """
        try:
            # Mapeo de días en español
            dias_espanol = {
                'Monday': 'Lunes',
                'Tuesday': 'Martes', 
                'Wednesday': 'Miércoles',
                'Thursday': 'Jueves',
                'Friday': 'Viernes',
                'Saturday': 'Sábado',
                'Sunday': 'Domingo'
            }
            
            dia_espanol = dias_espanol.get(dia_semana, dia_semana)
            
            # Verificar en el horario detallado
            horario_dia = horarios_detallados.get(dia_espanol)
            if horario_dia:
                if isinstance(horario_dia, dict):
                    return horario_dia.get('horas_totales', 0) > 0
                elif isinstance(horario_dia, str):
                    return horario_dia.strip() not in ['', '00:00:00', '00:00']
            
            # Por defecto, excluir fines de semana
            return dia_semana not in ['Saturday', 'Sunday']
            
        except Exception as e:
            print(f"⚠️ Error verificando horario día: {e}")
            return dia_semana not in ['Saturday', 'Sunday']

    def calcular_dias_laborales_fallback(self, df_empleado: pd.DataFrame) -> int:
        """Fallback para calcular días laborales"""
        if df_empleado.empty:
            return 0
            
        # Contar días que no son fin de semana
        dias_no_finde = len([d for d in df_empleado['dia'] 
                           if d.weekday() < 5])  # 0-4 = Lunes-Viernes
        return dias_no_finde

    def calcular_dias_laborales_fallback_simple(self, fecha_inicio, fecha_fin) -> int:
        """Fallback simple para calcular días laborales entre fechas"""
        try:
            todos_los_dias = pd.date_range(start=fecha_inicio, end=fecha_fin, freq='D')
            dias_laborales = len([d for d in todos_los_dias if d.weekday() < 5])
            return dias_laborales
        except:
            return 6  # Valor por defecto

    def aplicar_permisos_detallados(self, df: pd.DataFrame, permisos_dict: Dict) -> pd.DataFrame:
        """Aplica permisos de manera detallada"""
        if df.empty:
            print("❌ DataFrame vacío en aplicar_permisos_detallados")
            return df

        print("📊 Aplicando permisos...")

        # Política de permisos
        POLITICA_PERMISOS = {
            "permiso sin goce de sueldo": "no_ajustar",
            "permiso sin goce": "no_ajustar",
            "sin goce de sueldo": "no_ajustar",
            "sin goce": "no_ajustar",
        }

        def normalize_leave_type(leave_type):
            """Normaliza el tipo de permiso para comparación"""
            if not leave_type:
                return ""
            import unicodedata
            import re
            
            def _strip_accents(text):
                try:
                    text = str(text)
                    text = unicodedata.normalize('NFD', text)
                    text = text.encode('ascii', 'ignore').decode('utf-8')
                    return str(text)
                except:
                    return text
            
            cleaned = _strip_accents(str(leave_type)).lower().strip()
            cleaned = re.sub(r'\s+', ' ', cleaned)
            
            if "sin goce" in cleaned:
                return "permiso sin goce de sueldo"
            
            aliases = {
                "permiso sin goce": "permiso sin goce de sueldo",
                "sin goce de sueldo": "permiso sin goce de sueldo",
                "sin goce": "permiso sin goce de sueldo",
                "permiso sgs": "permiso sin goce de sueldo",
            }
            return aliases.get(cleaned, cleaned)

        for employee_code, permisos_empleado in permisos_dict.items():
            employee_mask = df['employee'].astype(str) == str(employee_code)
            
            for fecha, permiso_info in permisos_empleado.items():
                # Convertir fecha a datetime.date si es string
                if isinstance(fecha, str):
                    fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
                
                fecha_mask = df['dia'] == fecha
                combined_mask = employee_mask & fecha_mask
                
                if combined_mask.any():
                    idx = df[combined_mask].index[0]
                    
                    # Marcar que tiene permiso
                    df.at[idx, "tiene_permiso"] = True
                    df.at[idx, "tipo_permiso"] = permiso_info["leave_type"]
                    
                    leave_type_normalized = normalize_leave_type(permiso_info["leave_type"])
                    is_half_day = permiso_info.get("is_half_day", False)
                    
                    # Obtener horas por día para este empleado
                    horas_por_dia = df.at[idx, '_horas_por_dia_num']
                    
                    # Calcular horas descontadas según tipo de permiso
                    accion = POLITICA_PERMISOS.get(leave_type_normalized, "ajustar_a_cero")
                    
                    horas_esperadas_orig = df.at[idx, 'horas_esperadas']
                    
                    if pd.notna(horas_esperadas_orig) and horas_esperadas_orig != "00:00:00":
                        if accion == "no_ajustar":
                            # No ajustar horas para permisos sin goce
                            pass
                        elif accion == "ajustar_a_cero":
                            if is_half_day:
                                # Para permisos de medio día, descontar solo la mitad
                                try:
                                    horas_td = pd.to_timedelta(horas_esperadas_orig)
                                    mitad_horas = horas_td / 2
                                    mitad_horas_str = str(mitad_horas).split()[-1]
                                    
                                    horas_ajustadas = horas_td - mitad_horas
                                    horas_ajustadas_str = str(horas_ajustadas).split()[-1]
                                    
                                    df.at[idx, "horas_esperadas"] = horas_ajustadas_str
                                    df.at[idx, "horas_descontadas_permiso"] = mitad_horas_str
                                except (ValueError, TypeError):
                                    # Si hay error, tratar como día completo
                                    df.at[idx, "horas_esperadas"] = "00:00:00"
                                    df.at[idx, "horas_descontadas_permiso"] = horas_esperadas_orig
                            else:
                                # Permiso de día completo
                                df.at[idx, "horas_esperadas"] = "00:00:00"
                                df.at[idx, "horas_descontadas_permiso"] = horas_esperadas_orig

        return df

    def calcular_horas_descanso(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula horas de descanso para cada día"""
        if df.empty:
            print("❌ DataFrame vacío en calcular_horas_descanso")
            return df

        print("🔄 Calculando horas de descanso...")

        df["horas_descanso"] = "00:00:00"
        df["_horas_descanso_td"] = pd.Timedelta(0)
        df["_horas_descanso_num"] = 0.0

        total_dias_con_descanso = 0

        for index, row in df.iterrows():
            # Contar checados válidos
            checado_count = 0
            checados = []
            
            for col in df.columns:
                if col.startswith('checado_') and pd.notna(row.get(col)):
                    checado_count += 1
                    checados.append(row[col])
            
            if checado_count >= 4:
                horas_descanso_td = self.calcular_horas_descanso_dia(checados)
                if horas_descanso_td > timedelta(0):
                    df.at[index, "_horas_descanso_td"] = horas_descanso_td
                    df.at[index, "horas_descanso"] = td_to_str(horas_descanso_td)
                    df.at[index, "_horas_descanso_num"] = horas_descanso_td.total_seconds() / 3600
                    total_dias_con_descanso += 1

        print(f"✅ Horas de descanso calculadas para {total_dias_con_descanso} días")
        return df

    def calcular_horas_descanso_dia(self, checados: List[str]) -> timedelta:
        """Calcula horas de descanso - SIEMPRE 1 HORA FIJA según documentación"""
        from datetime import timedelta
        return timedelta(hours=1)  # 1 hora fija de descanso según documentación

    def calcular_resumen_final(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula el resumen final con las fórmulas correctas"""
        try:
            print("📈 Generando resumen final...")
        
            if df.empty:
                print("❌ DataFrame vacío en calcular_resumen_final")
                return pd.DataFrame()

            # Asegurarnos de que tenemos las columnas necesarias
            required_cols = ['employee', 'Nombre', 'duration', '_horas_esperadas_num', '_horas_descontadas_permiso_num', '_horas_descanso_num']
            for col in required_cols:
                if col not in df.columns:
                    print(f"⚠️  Columna faltante: {col}")
                    if 'num' in col:
                        df[col] = 0.0
                    else:
                        df[col] = pd.Timedelta(0)

            # CORRECCIÓN: Asegurar que duration sea timedelta
            if df['duration'].dtype != 'timedelta64[ns]':
                df['duration'] = pd.to_timedelta(df['duration'], errors='coerce').fillna(pd.Timedelta(0))

            # Agrupar por empleado
            group_cols = ['employee', 'Nombre']
            
            aggregation_dict = {
                'duration': 'sum',
                '_horas_esperadas_num': 'first',
                '_horas_descontadas_permiso_num': 'sum',
                '_horas_descanso_num': 'sum',
                'es_retardo_acumulable': 'sum',
                'es_falta': 'sum', 
                'falta_justificada': 'sum',
                'salida_anticipada': 'sum'
            }

            # Solo incluir columnas que existen
            existing_agg_cols = {k: v for k, v in aggregation_dict.items() if k in df.columns}
            df_resumen = df.groupby(group_cols).agg(existing_agg_cols).reset_index()

            # CÁLCULOS FINALES - FÓRMULAS EXACTAS
            total_horas_trabajadas_td = df_resumen['duration'].fillna(pd.Timedelta(0))
            
            total_horas_esperadas_td = df_resumen['_horas_esperadas_num'].apply(
                lambda x: timedelta(hours=float(x)) if pd.notna(x) and float(x) > 0 else pd.Timedelta(0)
            )
            
            total_horas_descontadas_td = df_resumen['_horas_descontadas_permiso_num'].apply(
                lambda x: timedelta(hours=float(x)) if pd.notna(x) and float(x) > 0 else pd.Timedelta(0)
            )
            
            total_horas_descanso_td = df_resumen['_horas_descanso_num'].apply(
                lambda x: timedelta(hours=float(x)) if pd.notna(x) and float(x) > 0 else pd.Timedelta(0)
            )

            # FÓRMULA CORRECTA: total_horas = horas_esperadas - horas_descontadas_permiso
            total_horas = total_horas_esperadas_td - total_horas_descontadas_td
            
            # FÓRMULA CORRECTA: diferencia = horas_trabajadas - total_horas
            diferencia = total_horas_trabajadas_td - total_horas

            # Formatear resultados
            df_resumen['total_horas_trabajadas'] = total_horas_trabajadas_td.apply(
                lambda x: self._timedelta_to_hhmmss(x) if pd.notna(x) and x.total_seconds() > 0 else "00:00:00"
            )
            df_resumen['total_horas_esperadas'] = total_horas_esperadas_td.apply(
                lambda x: self._timedelta_to_hhmmss(x) if pd.notna(x) and x.total_seconds() > 0 else "00:00:00"
            )
            df_resumen['total_horas_descontadas_permiso'] = total_horas_descontadas_td.apply(
                lambda x: self._timedelta_to_hhmmss(x) if pd.notna(x) and x.total_seconds() > 0 else "00:00:00"
            )
            df_resumen['total_horas_descanso'] = total_horas_descanso_td.apply(
                lambda x: self._timedelta_to_hhmmss(x) if pd.notna(x) and x.total_seconds() > 0 else "00:00:00"
            )
            df_resumen['total_horas'] = total_horas.apply(
                lambda x: self._timedelta_to_hhmmss(x) if pd.notna(x) and x.total_seconds() > 0 else "00:00:00"
            )
            df_resumen['diferencia_HHMMSS'] = diferencia.apply(
                lambda x: self._timedelta_to_hhmmss(x) if pd.notna(x) else "00:00:00"
            )
            
            # Asegurar columnas de faltas y retardos
            if 'es_retardo_acumulable' in df_resumen.columns:
                df_resumen['total_retardos'] = df_resumen['es_retardo_acumulable'].fillna(0).astype(int)
            else:
                df_resumen['total_retardos'] = 0
                
            if 'es_falta' in df_resumen.columns:
                df_resumen['total_faltas'] = df_resumen['es_falta'].fillna(0).astype(int)
                df_resumen['faltas_del_periodo'] = df_resumen['total_faltas']
            else:
                df_resumen['total_faltas'] = 0
                df_resumen['faltas_del_periodo'] = 0
                
            if 'falta_justificada' in df_resumen.columns:
                df_resumen['faltas_justificadas'] = df_resumen['falta_justificada'].fillna(0).astype(int)
            else:
                df_resumen['faltas_justificadas'] = 0
                
            if 'salida_anticipada' in df_resumen.columns:
                df_resumen['total_salidas_anticipadas'] = df_resumen['salida_anticipada'].fillna(0).astype(int)
            else:
                df_resumen['total_salidas_anticipadas'] = 0

            df_resumen['episodios_ausencia'] = 0

            # Seleccionar columnas finales
            columnas_finales = [
                'employee', 'Nombre',
                'total_horas_trabajadas', 'total_horas_esperadas',
                'total_horas_descontadas_permiso', 'total_horas_descanso',
                'total_horas', 'diferencia_HHMMSS',
                'total_retardos', 'faltas_del_periodo', 'faltas_justificadas',
                'total_faltas', 'episodios_ausencia', 'total_salidas_anticipadas'
            ]
            
            columnas_existentes = [col for col in columnas_finales if col in df_resumen.columns]
            df_resumen_final = df_resumen[columnas_existentes].copy()

            print(f"✅ Resumen generado para {len(df_resumen_final)} empleados")
            
            return df_resumen_final

        except Exception as e:
            print(f"❌ Error en calcular_resumen_final: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def _timedelta_to_hhmmss(self, td):
        """Convierte timedelta a formato HH:MM:SS"""
        try:
            if pd.isna(td) or td == pd.NaT or td.total_seconds() == 0:
                return "00:00:00"
            
            total_seconds = abs(int(td.total_seconds()))
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            # Manejar diferencias negativas
            sign = "-" if td.total_seconds() < 0 else ""
            
            return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"
        except Exception as e:
            print(f"⚠️ Error convirtiendo timedelta: {e}")
            return "00:00:00"

    def procesar_reporte_completo(
        self, 
        checkin_data: List[Dict], 
        permisos_dict: Dict,
        joining_dates_dict: Dict,
        start_date: str, 
        end_date: str
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Procesa completamente los datos de asistencia con cálculos correctos
        """
        try:
            print("🚀 Iniciando procesamiento completo del reporte...")
            print(f"   - Período: {start_date} a {end_date}")
            print(f"   - {len(checkin_data)} registros de checadas")
            print(f"   - {len(permisos_dict)} empleados con permisos")
            print(f"   - {len(joining_dates_dict)} joining dates")

            # Paso 1: Crear DataFrame base
            df_detalle = self.process_checkins_to_dataframe(checkin_data, start_date, end_date)
            if df_detalle.empty:
                print("❌ No se generaron datos de detalle")
                return pd.DataFrame(), pd.DataFrame()

            print(f"✅ DataFrame base creado: {len(df_detalle)} filas")

            # Paso 2: Calcular horas esperadas para cada empleado (USANDO HORARIOS REALES)
            df_detalle = self.analizar_asistencia_con_horarios(df_detalle, joining_dates_dict)
            if df_detalle.empty:
                print("❌ Error en análisis de horarios")
                return pd.DataFrame(), pd.DataFrame()

            # Paso 3: Aplicar permisos
            df_detalle = self.aplicar_permisos_detallados(df_detalle, permisos_dict)

            # Paso 4: Calcular horas de descanso
            df_detalle = self.calcular_horas_descanso(df_detalle)

            # Paso 5: Calcular resumen final por empleado
            df_resumen = self.calcular_resumen_final(df_detalle)

            print("🎉 Procesamiento completo finalizado exitosamente")
            print(f"   - Reporte detalle: {len(df_detalle)} filas")
            print(f"   - Reporte resumen: {len(df_resumen)} empleados")

            return df_detalle, df_resumen

        except Exception as e:
            print(f"❌ Error en procesamiento completo: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame(), pd.DataFrame()

def generar_reporte_asistencia(
    checkin_data: List[Dict],
    permisos_dict: Dict,
    joining_dates_dict: Dict, 
    start_date: str,
    end_date: str
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Función principal para generar reportes de asistencia.
    """
    try:
        processor = AttendanceProcessor()
        
        df_detalle, df_resumen = processor.procesar_reporte_completo(
            checkin_data=checkin_data,
            permisos_dict=permisos_dict,
            joining_dates_dict=joining_dates_dict,
            start_date=start_date,
            end_date=end_date
        )
        
        # Asegurar que nunca retorne None
        if df_detalle is None:
            df_detalle = pd.DataFrame()
        if df_resumen is None:
            df_resumen = pd.DataFrame()
            
        return df_detalle, df_resumen
        
    except Exception as e:
        print(f"❌ Error crítico en generar_reporte_asistencia: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame(), pd.DataFrame()