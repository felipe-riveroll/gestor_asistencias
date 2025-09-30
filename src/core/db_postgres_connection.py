def obtener_horario_empleado(*args):
    """
    VERSIÓN DEFINITIVA CORREGIDA - Sin errores de SQL
    """
    employee_code = args[0] if args else None
    
    print(f"🔍 Obteniendo horario para: {employee_code}")
    
    if not employee_code:
        return get_default_schedule()
    
    try:
        employee_id = int(employee_code)
        result = get_schedule_by_id(employee_id)
        if result:
            return result
    except (ValueError, TypeError) as e:
        print(f"❌ Error convirtiendo código: {e}")
    
    return get_default_schedule()

def get_schedule_by_id(employee_id):
    """Buscar horario por ID numérico"""
    try:
        from django.db import connection
        
        query = """
        SELECT 
            h.hora_entrada, 
            h.hora_salida, 
            h.cruza_medianoche,
            e.nombre || ' ' || e.apellido_paterno as nombre_completo
        FROM "AsignacionHorario" a
        INNER JOIN "Horario" h ON a.horario_id = h.horario_id
        INNER JOIN "Empleados" e ON a.empleado_id = e.empleado_id
        WHERE e.codigo_checador = %s OR e.codigo_frappe = %s
        LIMIT 1
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query, [employee_id, employee_id])
            result = cursor.fetchone()
            
            if result:
                print(f"✅ Horario encontrado para {employee_id}")
                return format_schedule_result(result)
            else:
                print(f"⚠️ No se encontró horario para {employee_id}")
                
    except Exception as e:
        print(f"❌ Error buscando por ID {employee_id}: {e}")
    
    return None

def format_schedule_result(result):
    """Formatear resultado de la consulta"""
    try:
        hora_entrada = str(result[0])
        hora_salida = str(result[1])
        
        if len(hora_entrada.split(':')) == 2:
            hora_entrada += ":00"
        if len(hora_salida.split(':')) == 2:
            hora_salida += ":00"
            
        horario = {
            'hora_entrada': hora_entrada,
            'hora_salida': hora_salida,
            'cruza_medianoche': bool(result[2]),
            'horas_totales': 8.0,
            'empleado_nombre': result[3] if len(result) > 3 else "Empleado",
            'fuente': 'base_datos'
        }
        
        print(f"   - ✅ Horario BD: {hora_entrada} - {hora_salida}")
        return horario
        
    except Exception as e:
        print(f"❌ Error formateando resultado: {e}")
        return get_default_schedule()

def get_default_schedule():
    """Horario por defecto"""
    print("   - 🔄 Usando horario por defecto")
    return {
        'hora_entrada': '08:00:00',
        'hora_salida': '17:00:00', 
        'cruza_medianoche': False,
        'horas_totales': 8.0,
        'empleado_nombre': 'No especificado',
        'fuente': 'por_defecto'
    }