from django.contrib import admin
# Asegúrate de importar TODOS tus modelos de core/models.py
from .models import Empleado, Horario, AsignacionHorario, Sucursal, DiaSemana 

# === 1. Configuración del Empleado (Tu código) ===
@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('empleado_id', 'nombre', 'apellido_paterno', 'codigo_frappe', 'codigo_checador', 'email')
    search_fields = ('nombre', 'apellido_paterno', 'codigo_frappe', 'email')

# === 2. REGISTRAR EL MODELO HORARIO (¡EL QUE FALTABA!) ===
# Esto te permitirá ver y eliminar los horarios flexibles (sin descripción)
@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ('horario_id', 'hora_entrada', 'hora_salida', 'cruza_medianoche', 'descripcion_horario')
    list_filter = ('cruza_medianoche',)
    search_fields = ('descripcion_horario', 'hora_entrada')

# === 3. Registrar Asignaciones y Sucursales (Opcional, pero recomendado) ===
@admin.register(AsignacionHorario)
class AsignacionHorarioAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'sucursal', 'horario', 'dia_especifico')
    list_filter = ('sucursal', 'horario', 'dia_especifico')

@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ('sucursal_id', 'nombre_sucursal')

@admin.register(DiaSemana)
class DiaSemanaAdmin(admin.ModelAdmin):
    list_display = ('dia_id', 'nombre_dia')