from django.contrib import admin
from django.urls import path
from core import views  # importa la vista

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.inicio, name='inicio'),  # <-- ruta raíz
    path('login/', views.login_view, name='login'),
    path("logout/", views.logout_view, name="logout"),
    path("admin-page/", views.admin_page, name="admin_page"),
    path("manager-page/", views.manager_page, name="manager-page"),
    path("admin-gestion-empleados/", views.gestion_empleados, name="admin-gestion-empleados"),
    path("empleados/crear/", views.crear_empleado, name="guardar_empleado"),
    path("empleados/eliminar/<int:empleado_id>/", views.eliminar_empleado, name="eliminar-empleado"),
    path("empleados/crear-horario/", views.crear_horario, name="crear_horario"),
    path("gestion_usuarios/", views.gestion_usuarios, name="gestion_usuarios"),
    path("lista_asistencias/", views.lista_asistencias, name="lista_asistencias"),
    path('health/', views.health_check, name='health_check'),
    path('api/reporte_horas/', views.api_reporte_horas, name='api_reporte_horas'),
    path('reporte_horas/', views.reporte_horas, name='reporte_horas'),
]