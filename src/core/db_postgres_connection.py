"""
Conexión a base de datos PostgreSQL para horarios - VERSIÓN CORREGIDA
Con fórmulas según documentación: Horas Efectivas = Horas Totales - 1 hora descanso (SIEMPRE)
"""

def obtener_horario_empleado_completo(employee_code: str, fecha: str = None):
    """
    VERSIÓN CORREGIDA - Siempre resta 1 hora de descanso
    """
    print(f"🔍 Obteniendo horario COMPLETO para: {employee_code}")
    
    if not employee_code:
        return _crear_horario_por_defecto()
    
    try:
        from django.db import connection
        
        # Convertir employee_code a entero
        employee_id = int(employee_code)
        
        # Determinar quincena basada en la fecha
        es_primera_quincena = True  # Por defecto
        if fecha:
            try:
                from datetime import datetime
                fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
                dia = fecha_dt.day
                es_primera_quincena = dia <= 15
                print(f"   📅 Fecha {fecha}: {'1ra' if es_primera_quincena else '2da'} quincena")
            except:
                pass
        
        # Llamar a la función PostgreSQL completa
        query = """
        SELECT * FROM f_tabla_horarios_multi_quincena('Todas')
        WHERE codigo_frappe = %s AND es_primera_quincena = %s
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query, [employee_id, es_primera_quincena])
            columns = [col[0] for col in cursor.description]
            result = cursor.fetchone()
            
            if result:
                horario_dict = dict(zip(columns, result))
                print(f"✅ Horario COMPLETO encontrado para {employee_code}")
                return _formatear_resultado_horario_corregido(horario_dict, employee_code)
            else:
                print(f"⚠️ No se encontró horario completo para {employee_code}")
                
    except Exception as e:
        print(f"❌ Error obteniendo horario completo: {e}")
    
    return _crear_horario_por_defecto(employee_code)

def _crear_horario_por_defecto(employee_code=None):
    """
    Crear horario por defecto con 1 hora de descanso FIJO
    """
    # Empleados con horario de 9 horas
    empleados_9_horas = ['1', '5', '6', '51', '52', '53', '57', '60', '62', '63', '78', '79', '87']
    
    if employee_code and str(employee_code) in empleados_9_horas:
        horas_totales_dia = 9.0
        horas_efectivas_dia = 8.0  # 9 - 1 descanso
        entrada = '08:00'
        salida = '18:00'
        print(f"   ⚡ Horario 9h: {employee_code} → 9.0 horas/día (8.0 efectivas)")
    else:
        horas_totales_dia = 8.0
        horas_efectivas_dia = 7.0  # 8 - 1 descanso
        entrada = '08:00'
        salida = '17:00'
        print(f"   ⚡ Horario 8h: {employee_code} → 8.0 horas/día (7.0 efectivas)")
    
    # Crear estructura detallada
    horarios_detallados = {}
    dias_laborales = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
    
    for dia in dias_laborales:
        horarios_detallados[dia] = {
            'entrada': entrada,
            'salida': salida,
            'horas_totales': horas_totales_dia,
            'horas_efectivas': horas_efectivas_dia,
            'horas_descanso': 1.0,
            'tiene_horario': True,
            'es_laboral': True
        }
    
    # Fines de semana sin horario
    for dia in ['Sábado', 'Domingo']:
        horarios_detallados[dia] = {
            'entrada': '00:00',
            'salida': '00:00',
            'horas_totales': 0.0,
            'horas_efectivas': 0.0,
            'horas_descanso': 0.0,
            'tiene_horario': False,
            'es_laboral': False
        }
    
    return {
        'empleado_id': employee_code or 'default',
        'empleado_nombre': f'Empleado {employee_code}' if employee_code else 'Empleado',
        'horas_totales_semana': horas_totales_dia * 5,
        'horas_efectivas_semana': horas_efectivas_dia * 5,
        'horas_por_dia': horas_totales_dia,
        'horas_efectivas_por_dia': horas_efectivas_dia,
        'dias_con_horario': 5,
        'dias_laborales': dias_laborales,
        'horarios_detallados': horarios_detallados,
        'fuente': 'default',
        'configuracion': {
            'descanso_fijo_horas': 1.0,
            'tolerancia_retardo_minutos': 10,
            'dias_laborales_semana': 5
        }
    }

def _formatear_resultado_horario_corregido(horario_dict: dict, employee_code: str):
    """
    VERSIÓN CORREGIDA - Siempre resta 1 hora de descanso
    """
    try:
        nombre_completo = horario_dict.get('nombre_completo', f'Empleado {employee_code}')
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        
        horas_totales_semana = 0.0
        horas_efectivas_semana = 0.0
        dias_con_horario = 0
        horarios_detallados = {}

        for dia in dias_semana:
            entrada = horario_dict.get(f'{dia.lower()}_entrada')
            salida = horario_dict.get(f'{dia.lower()}_salida')

            if entrada and salida and entrada != '00:00:00':
                try:
                    from datetime import datetime
                    entrada_dt = datetime.strptime(entrada, '%H:%M:%S')
                    salida_dt = datetime.strptime(salida, '%H:%M:%S')

                    # Calcular horas totales
                    diferencia = salida_dt - entrada_dt
                    horas_totales_dia = diferencia.total_seconds() / 3600

                    # ✅ CORRECCIÓN: SIEMPRE RESTAR 1 HORA DE DESCANSO
                    horas_efectivas_dia = horas_totales_dia - 1.0

                    # Asegurar que no sea negativo
                    if horas_efectivas_dia < 0:
                        horas_efectivas_dia = 0

                    horas_totales_semana += horas_totales_dia
                    horas_efectivas_semana += horas_efectivas_dia
                    dias_con_horario += 1

                    horarios_detallados[dia] = {
                        'entrada': entrada,
                        'salida': salida,
                        'horas_totales': round(horas_totales_dia, 2),
                        'horas_efectivas': round(horas_efectivas_dia, 2),
                        'horas_descanso': 1.0,
                        'tiene_horario': True,
                        'es_laboral': dia in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
                    }

                    print(f"   - {dia}: {entrada}-{salida} → {horas_totales_dia:.1f}h total, {horas_efectivas_dia:.1f}h efectivas")

                except Exception as e:
                    print(f"   ⚠️ Error calculando horas para {dia}: {e}")
                    # ✅ CORRECCIÓN: Valor por defecto con 1 hora descanso
                    horas_totales_dia = 9.0 if employee_code in ['1','5','6','51','52','53','57','60','62','63','78','79','87'] else 8.0
                    horas_efectivas_dia = horas_totales_dia - 1.0

                    horas_totales_semana += horas_totales_dia
                    horas_efectivas_semana += horas_efectivas_dia
                    dias_con_horario += 1

                    horarios_detallados[dia] = {
                        'entrada': '08:00',
                        'salida': '18:00' if horas_totales_dia == 9.0 else '17:00',
                        'horas_totales': horas_totales_dia,
                        'horas_efectivas': horas_efectivas_dia,
                        'horas_descanso': 1.0,
                        'tiene_horario': True,
                        'es_laboral': dia in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
                    }
            else:
                # Día sin horario
                horarios_detallados[dia] = {
                    'entrada': '00:00',
                    'salida': '00:00',
                    'horas_totales': 0.0,
                    'horas_efectivas': 0.0,
                    'horas_descanso': 0.0,
                    'tiene_horario': False,
                    'es_laboral': dia in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
                }

        # Calcular promedios
        horas_por_dia = horas_totales_semana / dias_con_horario if dias_con_horario > 0 else 8.0
        horas_efectivas_por_dia = horas_efectivas_semana / dias_con_horario if dias_con_horario > 0 else 7.0

        dias_laborales = [dia for dia in dias_semana if horarios_detallados[dia]['tiene_horario'] and horarios_detallados[dia]['es_laboral']]

        horario_completo = {
            'empleado_id': employee_code,
            'empleado_nombre': nombre_completo,
            'horas_totales_semana': round(horas_totales_semana, 2),
            'horas_efectivas_semana': round(horas_efectivas_semana, 2),
            'horas_por_dia': round(horas_por_dia, 2),
            'horas_efectivas_por_dia': round(horas_efectivas_por_dia, 2),
            'dias_con_horario': dias_con_horario,
            'dias_laborales': dias_laborales,
            'horarios_detallados': horarios_detallados,
            'fuente': 'base_datos',
            'configuracion': {
                'descanso_fijo_horas': 1.0,
                'tolerancia_retardo_minutos': 10,
                'dias_laborales_semana': 5
            }
        }

        print(f"   📊 Resumen: {dias_con_horario} días, {horas_totales_semana:.1f}h totales, {horas_efectivas_semana:.1f}h efectivas")
        return horario_completo

    except Exception as e:
        print(f"❌ Error formateando horario completo: {e}")
        return _crear_horario_por_defecto(employee_code)

def format_complete_schedule_result(horario_dict: dict, employee_code: str):
    """
    Alias para compatibilidad
    """
    return _formatear_resultado_horario_corregido(horario_dict, employee_code)