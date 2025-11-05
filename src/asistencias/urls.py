from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.inicio, name='inicio'),
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
    path('api/reporte_detalle/', views.api_reporte_detalle, name='api_reporte_detalle'),
    path('api/export_dashboard_excel/', views.export_dashboard_excel, name='export_dashboard_excel'),
    path("grafica_general/", views.grafica_general, name="grafica_general"),
    path("api/dashboard/general/", views.api_dashboard_general, name="api_dashboard_general"),
    path('api/exportar_excel_con_colores/', views.exportar_excel_con_colores, name='exportar_excel_con_colores'),
]