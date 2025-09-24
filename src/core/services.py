# Funcion para autenticar un usuario con Django Auth
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import Empleado, AsignacionHorario, Sucursal, Horario


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
