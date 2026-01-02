from django.contrib.auth.models import User, Group
from core.models import Empleado

# 1️⃣ Datos del nuevo usuario
nombre_usuario = "Elizabeth"  # nombre de usuario
correo = "elizabeth@example.com"
password = "12345678"

# 2️⃣ Crear usuario en Django Auth
user = User.objects.create_user(
    username=nombre_usuario,
    email=correo,
    password=password
)

# 3️⃣ Asignar como administrador (staff + superuser)
user.is_staff = True
user.save()
grupo = Group.objects.get(name="Admin") 
user.groups.add(grupo)
user.save()
print ("Usuario creado con éxito")

# 4️⃣ Vincular con el empleado
empleado = Empleado.objects.get(codigo_frappe=87)
empleado.user = user
empleado.save()

print(f"Usuario '{user.username}' creado y vinculado con {empleado.nombre}")