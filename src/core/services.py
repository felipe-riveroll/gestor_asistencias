# Imports de Python y librerías externas
from datetime import datetime, timedelta, time
from itertools import product
import pandas as pd
from typing import Dict, List, Tuple
import secrets
import string

# Imports de Django
from django.contrib.auth import authenticate
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings

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
from django.shortcuts import get_object_or_404

def autenticar_usuario(request, email, password):
    try:
        user_obj = User.objects.get(email=email)
        user = authenticate(request, username=user_obj.username, password=password)
        return user
    except User.DoesNotExist:
        return None

def crear_empleado_service(data):
    """Crea un empleado y sus asignaciones, validando duplicados en registros activos."""
    print("[DEBUG] POST crudo:", dict(data))

    # 1. Validar duplicados (objects ya filtra por is_deleted=False gracias al Manager)
    if Empleado.objects.filter(codigo_frappe=data.get("codigoFrappe")).exists():
        raise ValidationError("Ya existe un empleado activo con este código de frappe.")
    if Empleado.objects.filter(codigo_checador=data.get("codigoChecador")).exists():
        raise ValidationError("Ya existe un empleado activo con este código de checador.")
    if data.get("email") and Empleado.objects.filter(email=data.get("email")).exists():
        raise ValidationError("Ya existe un empleado activo con este email.")

    # 2. Crear empleado (por defecto es activo)
    empleado = Empleado.objects.create(
        codigo_frappe=data.get("codigoFrappe"),
        codigo_checador=data.get("codigoChecador"),
        nombre=data.get("nombre"),
        apellido_paterno=data.get("primerApellido"),
        apellido_materno=data.get("segundoApellido"),
        email=data.get("email"),
        tiene_horario_asignado=True,
    )
    print(f"[DEBUG] Empleado creado -> ID: {empleado.pk}, Nombre: {empleado.nombre}")

    # 3. Crear asignaciones...
    sucursales = data.getlist("sucursales[]")
    horarios = data.getlist("horarios[]")
    dias = data.getlist("dias[]")

    if not sucursales or not horarios or not dias:
        print("[ERROR] No llegaron datos de horarios/sucursales/días")
        return empleado

    for sucursal_id, horario_id, dias_str in zip(sucursales, horarios, dias):
        dias_list = dias_str.split(",")
        for dia in dias_list:
            try:
                horario = Horario.objects.get(pk=int(horario_id))
                AsignacionHorario.objects.create(
                    empleado=empleado,
                    sucursal_id=int(sucursal_id),
                    horario=horario,
                    dia_especifico_id=int(dia),
                    hora_entrada_especifica=horario.hora_entrada,
                    hora_salida_especifica=horario.hora_salida,
                    hora_salida_especifica_cruza_medianoche=horario.cruza_medianoche,
                )
            except Horario.DoesNotExist:
                print(f"[ERROR] Horario con ID {horario_id} no existe, saltando asignación.")
            except Exception as e:
                print(f"[ERROR] No se pudo crear asignación: {e}")
    return empleado

def listar_empleados():
    """
    Lista empleados activos que tienen al menos una asignación de horario.
    NOTA: Se corrige la consulta original, asumiendo que el objetivo es obtener
    los datos de Empleado a través de su Asignación. Usa el filtro is_deleted.
    """
    # Consulta optimizada: trae asignaciones relacionadas con empleado/sucursal/horario
    empleados_qs = AsignacionHorario.objects.select_related("empleado", "sucursal", "horario").all()

    # Filtramos y desduplicamos en Python
    lista_empleados = []
    empleados_procesados = set()

    for a in empleados_qs:
        emp = a.empleado
        # CRUCIAL: Solo incluimos si el empleado NO está eliminado (is_deleted=False)
        # y si aún no ha sido procesado
        if not emp.is_deleted and emp.empleado_id not in empleados_procesados:
            lista_empleados.append(
                {
                    "empleado_id": emp.empleado_id,
                    "nombre": emp.nombre,
                    "apellido_paterno": emp.apellido_paterno,
                    "apellido_materno": emp.apellido_materno,
                    "email": emp.email,
                    "codigo_frappe": emp.codigo_frappe,
                    "codigo_checador": emp.codigo_checador,
                }
            )
            empleados_procesados.add(emp.empleado_id)
            
    return lista_empleados

def crear_horario_service(data):
    """Crea un nuevo horario validando que no exista uno con la misma configuración."""
    hora_entrada = data.get("horaEntrada")
    hora_salida = data.get("horaSalida")
    cruza_medianoche = True if data.get("cruzaNoche") == "si" else False
    descripcion = data.get("descripcionHorario") or ""

    # Validar si ya existe un horario con la misma configuración
    if Horario.objects.filter(
        hora_entrada=hora_entrada,
        hora_salida=hora_salida,
        cruza_medianoche=cruza_medianoche,
    ).exists():
        raise ValidationError("Ya existe un horario con la misma configuración.")

    # Si no existe, lo creamos
    return Horario.objects.create(
        hora_entrada=hora_entrada,
        hora_salida=hora_salida,
        cruza_medianoche=cruza_medianoche,
        descripcion_horario=descripcion,
    )

# =================================================================
# === FUNCIONES DE GESTIÓN DE ROLES (USAN Empleado.objects para activos) ===
# =================================================================

def asignar_rol_service(data):
    """Asigna/edita roles de Administrador/Manager a un Empleado activo."""
    admin_id = data.get("adminId") 
    nombre = data.get("firstName")
    apellido = data.get("firstLastName")
    correo = data.get("email")
    codigo_frappe = data.get("frappeCode")
    print("[DEBUG] Codigo frappe recibido:", codigo_frappe)
    rol = data.get("role")

    if admin_id:
        # Modo edición: busca solo activos
        try:
            empleado = Empleado.objects.select_related("user").get(pk=admin_id)
        except Empleado.DoesNotExist:
            return {"error": "Empleado activo no encontrado."} # ⬅️ Corregido a 'activo'

        user = empleado.user
        if not user: return {"error": "Este empleado no tiene usuario asociado."}

        # Actualizar datos
        user.first_name = nombre; user.last_name = apellido; user.email = correo
        user.save()

        # Actualizar grupo
        user.groups.clear()
        if rol == "Admin":
             grupo, _ = Group.objects.get_or_create(name="Admin")
             user.is_superuser = True
        else:
             grupo, _ = Group.objects.get_or_create(name="Manager")
             user.is_superuser = False
        user.is_staff = True
        user.groups.add(grupo)
        user.save()

        return {"success": f"Administrador '{user.username}' actualizado correctamente."}

    # Modo creación: busca solo activos
    try:
        empleado = Empleado.objects.get(codigo_frappe=codigo_frappe) # Busca activo
    except Empleado.DoesNotExist:
        return {"error": "No existe un empleado ACTIVO con ese código Frappe."}

    # Validar si ya tiene usuario vinculado
    if empleado.user: return {"error": "Este empleado ya tiene un usuario asignado."}
    # Validar correo repetido
    if User.objects.filter(email=correo).exists(): return {"error": "Este correo ya está registrado."}

    # Crear usuario y vincular...
    username = correo.split("@")[0]
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for i in range(12))

    user = User.objects.create_user(
        username=username, email=correo, password=password, first_name=nombre, last_name=apellido,
    )

    # Asignar grupo y permisos
    if rol == "Admin":
        user.is_staff = True; user.is_superuser = True
        grupo, _ = Group.objects.get_or_create(name="Admin")
    else:
        user.is_staff = True; user.is_superuser = False
        grupo, _ = Group.objects.get_or_create(name="Manager")

    user.save(); user.groups.add(grupo)
    empleado.user = user; empleado.save()

    # Enviar correo con las credenciales
    asunto = "Credenciales de acceso al sistema"
    mensaje = (
        f"Hola {nombre},\n\nSe te ha creado un usuario en el sistema.\n\n"
        f"Usuario: {correo}\nContraseña: {password}\n\n"
        f"Por favor, ingresa con el correo y contraseña que se te asigno.\n\nSaludos."
    )
    send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [correo], fail_silently=False)

    return {"success": f"Usuario '{username}' creado y vinculado correctamente."}

def obtener_roles_service():
    # 1. Filtra empleados que tienen un usuario de Django asociado (es decir, tienen un rol)
    empleados_con_usuario = (
        Empleado.objects
        .select_related("user")
        .filter(user__isnull=False) # SOLO los que tienen rol asignado
    )

    resultado = []
    for emp in empleados_con_usuario:
        # 2. Obtiene los nombres de los grupos a los que pertenece el usuario
        grupos = emp.user.groups.values_list("name", flat=True)
        
        # 3. Determina el rol a mostrar
        rol = "—" # Valor por defecto

        if "Admin" in grupos:
            rol = "Admin"
        elif "Manager" in grupos:
            rol = "Manager"
        # Nota: Si un usuario está en ambos grupos, esta lógica lo catalogará como "Admin".
        
        resultado.append({
            "id": emp.empleado_id,
            "nombre_completo": f"{emp.nombre} {emp.apellido_paterno or ''} {emp.apellido_materno or ''}".strip(),
            "correo": emp.user.email,
            "codigo_frappe": emp.codigo_frappe,
            "rol": rol, # Aquí se muestra si es "Admin" o "Manager"
        })

    return resultado

def obtener_admin_por_id_service(empleado_id):
    try:
        empleado = Empleado.objects.select_related("user").get(pk=empleado_id) # Busca activo
        user = empleado.user

        if not user: return None

        grupos = user.groups.values_list("name", flat=True)
        rol = "Admin" if "Admin" in grupos else "Manager" if "Manager" in grupos else ""

        return {
            "empleado_id": empleado.empleado_id, "firstName": empleado.nombre, "firstLastName": empleado.apellido_paterno,
            "email": user.email, "frappeCode": empleado.codigo_frappe, "role": rol, "username": user.username,
        }

    except Empleado.DoesNotExist:
        return None

def eliminar_admin_service(empleado_id):
    try:
        empleado = Empleado.objects.select_related("user").get(pk=empleado_id) # Busca activo
    except Empleado.DoesNotExist:
        return {"error": "Empleado activo no encontrado."} # ⬅️ Corregido

    user = empleado.user
    if not user: return {"error": "Este empleado no tiene usuario asociado."}

    username = user.username
    empleado.user = None; empleado.save()
    user.delete()

    return {"success": f"El administrador '{username}' fue eliminado correctamente."}

# --- INICIA CORRECCIÓN 1: NUEVA FUNCIÓN AUXILIAR ---
def map_device_to_sucursal(device_id_str: str) -> str:
    """Convierte un 'device_id' (texto) en un nombre de Sucursal estandarizado."""
    if device_id_str is None: return 'Desconocida'
    device_id = str(device_id_str).lower()
    
    if 'villas' in device_id or 'vlla' in device_id: return 'Villas'
    if '31pte' in device_id or '31' in device_id or 'pte' in device_id: return '31pte'
    if 'nave' in device_id or 'nav' in device_id: return 'Nave'
    if 'rioblanco' in device_id or 'rio' in device_id or 'blanco' in device_id: return 'RioBlanco'
    return 'Desconocida'
# --- FIN CORRECCIÓN 1 ---

#Reporte de Horas y Lista de Asistencias
class AttendanceProcessor:
    
    def process_checkins_to_dataframe(self, checkin_data, start_date, end_date, employee_codes=None):
        df = pd.DataFrame(checkin_data) if checkin_data else pd.DataFrame(columns=['employee', 'time', 'device_id'])
        
        if 'time' in df.columns and not df.empty:
            df["time"] = pd.to_datetime(df["time"])
            df["dia"] = df["time"].dt.date
            df["checado_time"] = df["time"].dt.time
            
            if 'device_id' not in df.columns: df['device_id'] = None
            df['Sucursal'] = df['device_id'].apply(map_device_to_sucursal)
        else:
            if 'device_id' not in df.columns: df['device_id'] = None
            if 'Sucursal' not in df.columns: df['Sucursal'] = None

        all_employees = employee_codes if employee_codes else (df["employee"].unique() if not df.empty else [])
        if not all_employees: return pd.DataFrame()

        all_dates = pd.date_range(start=start_date, end=end_date, freq='D').date
        base_df = pd.DataFrame(list(product(all_employees, all_dates)), columns=['employee', 'dia'])

        if not df.empty:
            stats = df.groupby(["employee", "dia"]).agg(
                checado_primero=('checado_time', 'min'), checado_ultimo=('checado_time', 'max'),
                checados_count=('time', 'count'), Sucursal=('Sucursal', 'first'), device_id=('device_id', 'first') 
            ).reset_index()
            
            def calc_duration(r):
                if r["checados_count"] < 2 or pd.isna(r['checado_primero']): return pd.Timedelta(0)
                d = datetime(2000, 1, 1)
                return datetime.combine(d, r['checado_ultimo']) - datetime.combine(d, r['checado_primero'])
            
            stats["duration"] = stats.apply(calc_duration, axis=1)
            final_df = base_df.merge(stats, on=['employee', 'dia'], how='left')
        else:
            final_df = base_df
        
        for col in ['duration', 'checados_count', 'checado_primero', 'checado_ultimo', 'Sucursal', 'device_id']:
            if col not in final_df.columns:
                if col == 'duration': final_df[col] = pd.Timedelta(0)
                elif col == 'checados_count': final_df[col] = 0
                else: final_df[col] = None
        
        final_df['duration'] = final_df['duration'].fillna(pd.Timedelta(0))
        final_df['checados_count'] = final_df['checados_count'].fillna(0).astype(int)
        
        final_df['Sucursal'] = final_df.groupby('employee')['Sucursal'].ffill().bfill()
        final_df['Sucursal'] = final_df['Sucursal'].fillna('Sin Asignar')

        # CRUCIAL: Solo mapear empleados ACTIVOS para los reportes
        empleados_activos_qs = Empleado.objects.filter(codigo_frappe__in=all_employees)
        emp_map = {str(e.codigo_frappe): f"{e.nombre} {e.apellido_paterno}" for e in empleados_activos_qs}
        
        final_df['Nombre'] = final_df['employee'].map(emp_map).fillna(final_df['employee'])
        
        final_df["dia_obj"] = pd.to_datetime(final_df["dia"])
        final_df["dia_semana"] = final_df["dia_obj"].dt.day_name()
        return final_df


    def analizar_asistencia_con_horarios(self, df: pd.DataFrame, start_date_str: str, end_date_str: str) -> pd.DataFrame:
        if df.empty: return df
        
        for col in ["horas_esperadas", "horario_entrada", "horario_salida"]:
            if 'horas' in col: df[col] = pd.Timedelta(0)
            else: df[col] = None

        employees_to_fetch = df["employee"].unique()
        if len(employees_to_fetch) == 0: return df
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        
        try:
             # Llama a tu función de conexión a la DB
             horarios_periodo = {e: obtener_horario_empleado_completo(e, start_date.strftime('%Y-%m-%d')) for e in employees_to_fetch}
        except NameError:
             # Si el import de db_postgres_connection falla, usa un diccionario vacío
             horarios_periodo = {}
        
        for idx, row in df.iterrows():
            horario_emp = horarios_periodo.get(row['employee'])
            if not horario_emp or horario_emp.get('dias_con_horario', 0) == 0: continue
            
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
            'Nombre': 'first', 'duration': 'sum', 'horas_esperadas': 'sum',
            'horas_permiso': 'sum', 'horas_descanso': 'sum', 'falta': 'sum', 'retardo': 'sum', 'salida_anticipada': 'sum',
            'falta_justificada': 'sum', 'episodio_ausencia_diario': 'sum',
        }
        
        df_resumen = df.groupby(['employee', 'Sucursal']).agg(agg_dict).reset_index().rename(columns={
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
                           'faltas_del_periodo', 'faltas_justificadas', 'episodios_ausencia',
                           'total_horas_trabajadas_td', 'total_horas_esperadas_td','total_horas_td']]


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
            
            descansos_calculados.append({'employee': empleado, 'dia': dia, 'horas_descanso': total_descanso_dia})
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
        if df_checadas.empty or 'time' not in df_checadas.columns: return pd.DataFrame()
        
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
            df_copy['falta'] == 1, (first_check - entry_schedule).dt.total_seconds() > (30 * 60), 
            df_copy['salida_anticipada'] == 1, df_copy['retardo'] == 1, df_copy['tiene_permiso'] == True, 
            (df_copy['horas_esperadas'].dt.total_seconds() == 0) & (df_copy['checados_count'] == 0), 
            (df_copy['retardo'] == 1) & (df_copy['duration'] >= df_copy['horas_esperadas']), 
        ]
        
        choices = ['Falta', 'Retardo Mayor', 'Salida Anticipada', 'Retardo Normal', 'Permiso', 'Descanso', 'Cumplió con horas']
        
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
            if col in df_detalle.columns: df_detalle[col] = df_detalle[col].apply(td_to_str)
        
        for col in df_detalle.columns:
            if col.startswith('checado_') or col.startswith('horario_'):
                df_detalle[col] = df_detalle[col].apply(lambda x: x.strftime('%H:%M:%S') if pd.notna(x) and not isinstance(x, str) else x)

        df_detalle['dia_semana'] = df_detalle['dia_semana'].map(DIAS_ESPANOL).fillna(df_detalle['dia_semana'])
        df_detalle['dia'] = df_detalle['dia'].astype(str)
        df_detalle.fillna('-', inplace=True)
        return df_detalle

# --- FUNCIONES PARA GRÁFICA GENERAL (USAN PANDAS) ---

def calcular_metricas_adicionales(df_resumen: pd.DataFrame, df_detalle: pd.DataFrame) -> pd.DataFrame:
    columnas_finales = ['ID', 'Nombre', 'Faltas', 'Puntualidad (%)', 'Eficiencia (%)',
                        'SIC', 'Sucursal', 'dias_laborables', 'Tasa Ausentismo (%)', 'Índice Puntualidad (%)', 'Eficiencia Horas (%)',
                        'Faltas Justificadas'] 
    df_resumen_final_vacio = pd.DataFrame(columns=columnas_finales)

    if df_resumen is None or df_detalle is None or df_resumen.empty or df_detalle.empty: return df_resumen_final_vacio

    required_cols_resumen = ['employee', 'total_horas_trabajadas_td', 'total_horas_td',
                             'total_retardos', 'faltas_del_periodo', 'episodios_ausencia',
                             'total_salidas_anticipadas', 'faltas_justificadas',
                             'Sucursal', 'Nombre']
    required_cols_detalle = ['employee', 'horas_esperadas', 'Sucursal'] 
    
    missing_resumen_cols = [col for col in required_cols_resumen if col not in df_resumen.columns]
    missing_detalle_cols = [col for col in required_cols_detalle if col not in df_detalle.columns]

    if missing_resumen_cols or missing_detalle_cols: return df_resumen_final_vacio
    
    df_resumen_calc = df_resumen.copy(); df_detalle_calc = df_detalle.copy()

    df_resumen_calc['total_horas_trabajadas_td'] = pd.to_timedelta(df_resumen_calc['total_horas_trabajadas_td'], errors='coerce').fillna(pd.Timedelta(0))
    df_resumen_calc['total_horas_td'] = pd.to_timedelta(df_resumen_calc['total_horas_td'], errors='coerce').fillna(pd.Timedelta(0))
    df_resumen_calc['total_retardos'] = pd.to_numeric(df_resumen_calc['total_retardos'], errors='coerce').fillna(0)
    df_resumen_calc['faltas_del_periodo'] = pd.to_numeric(df_resumen_calc['faltas_del_periodo'], errors='coerce').fillna(0)
    df_resumen_calc['total_salidas_anticipadas'] = pd.to_numeric(df_resumen_calc['total_salidas_anticipadas'], errors='coerce').fillna(0)
    df_resumen_calc['episodios_ausencia'] = pd.to_numeric(df_resumen_calc['episodios_ausencia'], errors='coerce').fillna(0)
    
    if not pd.api.types.is_timedelta64_dtype(df_detalle_calc['horas_esperadas']):
        df_detalle_calc['horas_esperadas'] = pd.to_timedelta(df_detalle_calc['horas_esperadas'], errors='coerce').fillna(pd.Timedelta(0))

    dias_laborables = df_detalle_calc[df_detalle_calc['horas_esperadas'].dt.total_seconds() > 0].groupby(['employee', 'Sucursal']).size()
    dias_laborables.name = 'dias_laborables'
    
    df_resumen_calc['employee'] = df_resumen_calc['employee'].astype(str)
    df_resumen_calc['Sucursal'] = df_resumen_calc['Sucursal'].astype(str)
    dias_laborables.index = dias_laborables.index.set_levels([dias_laborables.index.levels[0].astype(str), dias_laborables.index.levels[1].astype(str)])

    df_resumen_calc = df_resumen_calc.merge(dias_laborables, on=['employee', 'Sucursal'], how='left')

    df_resumen_calc['dias_laborables'] = df_resumen_calc['dias_laborables'].fillna(0).astype(int)
    mask_dlp = df_resumen_calc['dias_laborables'] > 0

    total_horas_trabajadas_s = df_resumen_calc['total_horas_trabajadas_td'].dt.total_seconds()
    total_horas_netas_s = df_resumen_calc['total_horas_td'].dt.total_seconds()
    df_resumen_calc['efficiency'] = 100.0
    mask_hnp = total_horas_netas_s > 0
    if mask_hnp.any():
        df_resumen_calc.loc[mask_hnp, 'efficiency'] = np.divide(
            total_horas_trabajadas_s[mask_hnp], total_horas_netas_s[mask_hnp],
            out=np.full_like(total_horas_trabajadas_s[mask_hnp], 100.0), where=total_horas_netas_s[mask_hnp]!=0
        ) * 100
    df_resumen_calc['efficiency'] = df_resumen_calc['efficiency'].fillna(100)

    df_resumen_calc['punctuality'] = 100.0
    if mask_dlp.any():
        denom = df_resumen_calc.loc[mask_dlp, 'dias_laborables'].astype(float)
        numer = denom - df_resumen_calc.loc[mask_dlp, 'total_retardos'].astype(float)
        df_resumen_calc.loc[mask_dlp, 'punctuality'] = np.divide(numer.clip(lower=0), denom, out=np.full_like(numer, 100.0), where=denom!=0) * 100
    df_resumen_calc['punctuality'] = df_resumen_calc['punctuality'].fillna(100).clip(0, 100)

    df_resumen_calc['sic'] = 100.0
    if mask_dlp.any():
        denom = df_resumen_calc.loc[mask_dlp, 'dias_laborables'].astype(float)
        faltas = df_resumen_calc.loc[mask_dlp, 'faltas_del_periodo']
        retardos = df_resumen_calc.loc[mask_dlp, 'total_retardos']
        salidas = df_resumen_calc.loc[mask_dlp, 'total_salidas_anticipadas']
        
        numer = denom - (faltas + retardos + salidas)
        
        df_resumen_calc.loc[mask_dlp, 'sic'] = np.divide(numer.clip(lower=0), denom, out=np.full_like(numer, 100.0), where=denom!=0) * 100
    
    df_resumen_calc['sic'] = df_resumen_calc['sic'].fillna(100).clip(0, 100)

    df_resumen_calc['tasa_ausentismo'] = 0.0
    if mask_dlp.any():
        denom = df_resumen_calc.loc[mask_dlp, 'dias_laborables'].astype(float)
        numer = df_resumen_calc.loc[mask_dlp, 'faltas_del_periodo'].astype(float)
        df_resumen_calc.loc[mask_dlp, 'tasa_ausentismo'] = np.divide(numer, denom, out=np.zeros_like(numer), where=denom!=0) * 100
    df_resumen_calc['tasa_ausentismo'] = df_resumen_calc['tasa_ausentismo'].fillna(0).clip(0, 100)
    
    df_resumen_calc['productivity'] = df_resumen_calc['efficiency']

    for col in ['efficiency', 'punctuality', 'sic', 'productivity', 'tasa_ausentismo']:
          if col in df_resumen_calc.columns: df_resumen_calc[col] = df_resumen_calc[col].round(1)

    rename_map = {
          'employee': 'ID', 'Nombre': 'Nombre', 'faltas_del_periodo': 'Faltas',
          'tasa_ausentismo': 'Tasa Ausentismo (%)', 'punctuality': 'Puntualidad (%)', 
          'efficiency': 'Eficiencia (%)', 'punctuality': 'Índice Puntualidad (%)',
          'efficiency': 'Eficiencia Horas (%)', 'sic': 'SIC', 'Sucursal': 'Sucursal', 
          'dias_laborables': 'dias_laborables', 'total_retardos': 'Retardos',
          'faltas_justificadas': 'Faltas Justificadas',
    }
    
    cols_to_rename = {k: v for k, v in rename_map.items() if k in df_resumen_calc.columns}
    df_resumen_final = df_resumen_calc.rename(columns=cols_to_rename)
    
    for col in columnas_finales:
        if col not in df_resumen_final.columns:
            if col in ['Faltas', 'dias_laborables', 'Faltas Justificadas']: df_resumen_final[col] = 0
            elif col in ['Puntualidad (%)', 'Eficiencia (%)', 'SIC', 'Tasa Ausentismo (%)', 'Índice Puntualidad (%)', 'Eficiencia Horas (%)']: df_resumen_final[col] = 0.0
            else: df_resumen_final[col] = 'N/A'

    return df_resumen_final[list(set(df_resumen_final.columns).intersection(set(columnas_finales)))]


def agregar_datos_dashboard_por_sucursal(df_metricas: pd.DataFrame) -> List[Dict]:
    col_id = 'ID'; col_eficiencia = 'Eficiencia Horas (%)'; col_puntualidad = 'Índice Puntualidad (%)'
    col_sic = 'SIC'; col_faltas_injustificadas = 'Faltas'; col_faltas_justificadas = 'Faltas Justificadas'
    col_sucursal = 'Sucursal'

    required_cols_for_grouping = [col_id, col_eficiencia, col_puntualidad, col_sic, col_faltas_injustificadas, col_sucursal, col_faltas_justificadas]
    
    if df_metricas is None or df_metricas.empty or not all(col in df_metricas.columns for col in required_cols_for_grouping):
        return []

    df_sucursales = df_metricas.groupby(col_sucursal).agg(
        employees=(col_id, 'nunique'), efficiency=(col_eficiencia, 'mean'),
        punctuality=(col_puntualidad, 'mean'), avgSIC=(col_sic, 'mean'),
        absences=(col_faltas_injustificadas, 'sum'), total_justified_absences=(col_faltas_justificadas, 'sum')
    ).reset_index()

    df_sucursales.rename(columns={col_sucursal: 'name'}, inplace=True)
    df_sucursales['productivity'] = df_sucursales['efficiency']

    for col in ['efficiency', 'punctuality', 'avgSIC', 'productivity']:
        if col in df_sucursales.columns: df_sucursales[col] = df_sucursales[col].round(1)

    df_sucursales['employees'] = df_sucursales['employees'].astype(int)
    df_sucursales['absences'] = df_sucursales['absences'].astype(int)
    df_sucursales['total_justified_absences'] = df_sucursales['total_justified_absences'].astype(int)

    return df_sucursales.to_dict('records')

def actualizar_datos_basicos_empleado_service(empleado_id, data):
    """Actualiza los datos personales básicos de un empleado activo."""
    empleado = get_object_or_404(Empleado.objects, pk=empleado_id) # Usa objects para buscar activo
    
    empleado.codigo_frappe = data.get("codigoFrappeEdit")
    empleado.codigo_checador = data.get("codigoChecadorEdit")
    empleado.nombre = data.get("nombreEdit")
    empleado.apellido_paterno = data.get("primerApellidoEdit")
    empleado.apellido_materno = data.get("segundoApellidoEdit")
    empleado.email = data.get("emailEdit")
    
    empleado.save()
    return empleado

def actualizar_horarios_empleado_service(empleado_id, data):
    """Borra y recrea las asignaciones de horario para un empleado activo."""
    from django.core.exceptions import ValidationError
    
    try:
        empleado = get_object_or_404(Empleado.objects, pk=empleado_id) # Usa objects para buscar activo

        AsignacionHorario.objects.filter(empleado=empleado).delete()
        
        sucursales = data.getlist("sucursales[]"); horarios = data.getlist("horarios[]"); dias = data.getlist("dias[]")
        if not sucursales: return empleado 

        for sucursal_id, horario_id, dias_str in zip(sucursales, horarios, dias):
            dias_list = dias_str.split(",")
            for dia in dias_list:
                horario_obj = Horario.objects.get(pk=int(horario_id))
                AsignacionHorario.objects.create(
                    empleado=empleado, sucursal_id=int(sucursal_id), horario=horario_obj,
                    dia_especifico_id=int(dia), hora_entrada_especifica=horario_obj.hora_entrada,
                    hora_salida_especifica=horario_obj.hora_salida,
                    hora_salida_especifica_cruza_medianoche=horario_obj.cruza_medianoche,
                )
        return empleado

    except Exception as e:
        raise ValidationError(f"Error al guardar horarios: {e}")