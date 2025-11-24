from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.inicio, name='inicio'),
    path('login/', views.login_view, name='login'),
    path("logout/", views.logout_view, name="logout"),
    path("admin-page/", views.admin_page, name="admin_page"),
    path("admin-page/<int:empleado_id>/editar/", views.admin_page, name="editar_admin"),
    path("admin-page/<int:empleado_id>/eliminar/", views.eliminar_admin, name="eliminar_admin"),
    path("manager-page/", views.manager_page, name="manager-page"),
    path("admin-gestion-empleados/", views.gestion_empleados, name="admin-gestion-empleados"),
    path("empleados/crear/", views.crear_empleado, name="guardar_empleado"),
    path("empleados/eliminar/<int:empleado_id>/", views.eliminar_empleado, name="eliminar-empleado"),
    # ----------------------------------------------------
    # 🟢 CAMBIO CRÍTICO 1: URL para Formulario 1 (Datos Personales/Email)
    # ----------------------------------------------------
    path('empleados/editar-datos-basicos/<int:empleado_id>/', views.editar_datos_basicos_empleado, name='editar_datos_basicos'),
    path('empleados/editar/<int:empleado_id>/', views.editar_empleado, name='editar-empleado'),
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
    path("grafica_31pte/",views.grafica_31pte,name='grafica_31pte'),
    path('api/dashboard/31pte/', views.api_dashboard_31pte, name='api-dashboard-31pte'),
    path("grafica_villas/",views.grafica_villas,name='grafica_villas'),
    path('api/dashboard/villas/', views.api_dashboard_villas, name='api-dashboard-villas'),
    path("grafica_nave/",views.grafica_nave,name='grafica_nave'),
    path('api/dashboard/nave/', views.api_dashboard_nave, name='api-dashboard-nave'),
    # === ¡AGREGA ESTAS DOS LÍNEAS AQUÍ! ===
    path('api/lista_sucursales/', views.api_lista_sucursales, name='api_lista_sucursales'),
    path('api/lista_horarios/', views.api_lista_horarios, name='api_lista_horarios'),
    # ========================================
    path('api/empleado/<int:empleado_id>/horarios/', views.get_horarios_empleado, name='api_horarios_empleado'),
    # En urls.py, dentro de urlpatterns
    path('api/horarios/eliminar/<int:horario_id>/', views.api_eliminar_horario_flexible, name='api_eliminar_horario'),
    # 🟢 RUTA AÑADIDA PARA EXPORTAR EL EXCEL DE LA LISTA DE EMPLEADOS 🟢
    path("admin-gestion-empleados/exportar/excel/", views.exportar_lista_empleados_excel, name="exportar_lista_empleados_excel"),
    # ----------------------------------------------------
]