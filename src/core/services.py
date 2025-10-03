# Funcion para autenticar un usuario con Django Auth
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import Empleado, AsignacionHorario, Sucursal, Horario
from django.core.exceptions import ValidationError

def autenticar_usuario(request, email, password):
    try:
        user_obj = User.objects.get(email=email)
        user = authenticate(request, username=user_obj.username, password=password)
        return user
    except User.DoesNotExist:
        return None

def crear_empleado_service(data):
    print("[DEBUG] POST crudo:", dict(data))

    # 1. Validar duplicados por código o email
    if Empleado.objects.filter(codigo_frappe=data.get("codigoFrappe")).exists():
        raise ValidationError("Ya existe un empleado con este código de frappe.")
    
    if Empleado.objects.filter(codigo_checador=data.get("codigoChecador")).exists():
        raise ValidationError("Ya existe un empleado con este código de checador.")
    
    if Empleado.objects.filter(email=data.get("email")).exists():
        raise ValidationError("Ya existe un empleado con este email.")

    # 2. Crear empleado
    empleado = Empleado.objects.create(
        codigo_frappe=data.get("codigoFrappe"),
        codigo_checador=data.get("codigoChecador"),
        nombre=data.get("nombre"),
        apellido_paterno=data.get("primerApellido"),
        apellido_materno=data.get("segundoApellido"),
        email=data.get("email"),
        tiene_horario_asignado=True
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
    hora_entrada = data.get("horaEntrada")
    hora_salida = data.get("horaSalida")
    cruza_medianoche = True if data.get("cruzaNoche") == "si" else False
    descripcion = data.get("descripcionHorario") or ""

    # Validar si ya existe un horario con la misma configuración
    if Horario.objects.filter(
        hora_entrada=hora_entrada,
        hora_salida=hora_salida,
        cruza_medianoche=cruza_medianoche
    ).exists():
        raise ValidationError("Ya existe un horario con la misma configuración.")

    # Si no existe, lo creamos
    return Horario.objects.create(
        hora_entrada=hora_entrada,
        hora_salida=hora_salida,
        cruza_medianoche=cruza_medianoche,
        descripcion_horario=descripcion,
    )
