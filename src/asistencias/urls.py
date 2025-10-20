from django.contrib import admin
from django.urls import path
from core import views  # importa la vista

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.inicio, name='inicio'),  # <-- ruta raíz
    path('login/', views.login_view, name='login'),
    path("logout/", views.logout_view, name="logout"),
    
    #Administracion de Roles
    path("admin-page/", views.admin_page, name="admin_page"),
    path("admin-page/<int:empleado_id>/editar/", views.admin_page, name="editar_admin"),
    path("admin-page/<int:empleado_id>/eliminar/", views.eliminar_admin, name="eliminar_admin"),
    
    #Manager
    path("manager-page/", views.manager_page, name="manager-page"),
    
    #Gestion de Empleados y Horarios
    path("admin-gestion-empleados/", views.gestion_empleados, name="admin-gestion-empleados"),
    path("empleados/crear/", views.crear_empleado, name="guardar_empleado"),
    path("empleados/eliminar/<int:empleado_id>/", views.eliminar_empleado, name="eliminar-empleado"),
    path("empleados/crear-horario/", views.crear_horario, name="crear_horario"),
]
