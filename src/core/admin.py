from django.contrib import admin
from .models import Empleado  # Importa tu modelo Empleado

# Opcional: Esto es para que la lista se vea bonita
class EmpleadoAdmin(admin.ModelAdmin):
    # ¡Pon aquí los nombres de los campos que quieres ver en la lista!
    # ¡CORREGIDO! Usamos los nombres de campos reales de tu models.py
    list_display = ('nombre', 'apellido_paterno', 'apellido_materno', 'codigo_frappe') 

    # ¡CORREGIDO! Usamos los campos reales para permitir la búsqueda
    search_fields = ('nombre', 'apellido_paterno', 'apellido_materno', 'codigo_frappe')

# REGISTRA TU MODELO
# Le decimos a Django que "muestre el modelo Empleado en el admin,
# usando la configuración de la clase EmpleadoAdmin"
admin.site.register(Empleado, EmpleadoAdmin)
# Register your models here.
