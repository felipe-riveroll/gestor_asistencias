# core/tests.py
"""Suite de regresión de seguridad para los 3 hallazgos del review adversarial.

H1 — Escalada de privilegios en `admin_page` / `asignar_rol_service`.
H2 — Edición de horario no atómica en `actualizar_horarios_empleado_service`.
H3 — Borrado de horario sin autorización ni protección referencial.
"""
from datetime import time

from django.contrib.auth.models import Group, User
from django.core import mail
from django.http import QueryDict
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import AsignacionHorario, DiaSemana, Empleado, Horario, Sucursal
from core.services import asignar_rol_service


# --------------------------------------------------------------------------
# Helpers compartidos
# --------------------------------------------------------------------------
def _grupo(nombre):
    g, _ = Group.objects.get_or_create(name=nombre)
    return g


def _admin(username="admin"):
    u = User.objects.create_user(username=username, email=f"{username}@test.test", password="x")
    u.is_superuser = True
    u.is_staff = True
    u.save()
    u.groups.add(_grupo("Admin"))
    return u


def _manager(username="manager"):
    u = User.objects.create_user(username=username, email=f"{username}@test.test", password="x")
    u.is_staff = True
    u.save()
    u.groups.add(_grupo("Manager"))
    return u


def _empleado(codigo, nombre="Empleado", user=None):
    emp = Empleado.objects.create(
        codigo_frappe=codigo,
        codigo_checador=codigo * 10,
        nombre=nombre,
        apellido_paterno="Test",
        email=f"emp{codigo}@test.test",
    )
    if user is not None:
        emp.user = user
        emp.save()
    return emp


def _horario(descripcion, entrada=time(8, 0), salida=time(16, 0)):
    return Horario.objects.create(
        hora_entrada=entrada,
        hora_salida=salida,
        descripcion_horario=descripcion,
    )


# --------------------------------------------------------------------------
# H1 — Escalada de privilegios
# --------------------------------------------------------------------------
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PrivilegiosAdminTest(TestCase):
    def setUp(self):
        self.manager = _manager()
        self.admin = _admin()
        # Empleado activo sin usuario (objetivo de la creación).
        self.objetivo = _empleado(1001, nombre="Objetivo")

    def test_manager_no_puede_promocionar_admin_via_vista(self):
        """Un Manager autenticado recibe 403 y no se crea ningún Admin."""
        self.client.force_login(self.manager)
        data = {
            "firstName": "X",
            "firstLastName": "Y",
            "email": "nuevo@test.test",
            "frappeCode": "1001",
            "role": "Admin",
        }
        resp = self.client.post(reverse("admin_page"), data=data)

        self.assertEqual(resp.status_code, 403)
        self.assertFalse(User.objects.filter(email="nuevo@test.test").exists())
        self.assertEqual(mail.outbox, [])  # no se envió correo de credenciales

    def test_manager_no_puede_eliminar_admin(self):
        """El endpoint de borrado de admin también queda bloqueado para Manager."""
        admin_user = User.objects.create_user(
            username="borrar", email="borrar@test.test", password="x"
        )
        emp = _empleado(1002, nombre="Borrar", user=admin_user)

        self.client.force_login(self.manager)
        resp = self.client.get(reverse("eliminar_admin", args=[emp.empleado_id]))

        self.assertEqual(resp.status_code, 403)
        self.assertTrue(User.objects.filter(pk=admin_user.pk).exists())

    def test_servicio_rechaza_actor_sin_permiso(self):
        """Defensa en profundidad: el servicio mismo rechaza a un actor no Admin."""
        qd = QueryDict("", mutable=True)
        qd.setlist("sucursales", [])  # contenido irrelevante: el guard actúa primero
        resultado = asignar_rol_service(qd, self.manager)

        self.assertIn("error", resultado)
        self.assertEqual(mail.outbox, [])

    def test_admin_puede_editar_rol(self):
        """Regresión: un Admin legítimo sí puede editar (no hay falso positivo)."""
        admin_user = User.objects.create_user(
            username="editar", email="editar@test.test", password="x"
        )
        admin_user.groups.add(_grupo("Admin"))
        admin_user.is_superuser = True
        admin_user.save()
        emp = _empleado(1003, nombre="Editar", user=admin_user)

        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("admin_page"),
            data={
                "adminId": str(emp.empleado_id),
                "firstName": "Editar",
                "firstLastName": "Test",
                "email": "editar@test.test",
                "role": "Manager",
            },
        )

        self.assertEqual(resp.status_code, 302)
        admin_user.refresh_from_db()
        self.assertTrue(admin_user.groups.filter(name="Manager").exists())
        self.assertFalse(admin_user.is_superuser)


# --------------------------------------------------------------------------
# H2 — Atomicidad en la edición de horarios
# --------------------------------------------------------------------------
class EdicionHorarioTest(TestCase):
    def setUp(self):
        self.admin = _admin()
        self.sucursal = Sucursal.objects.create(nombre_sucursal="Sucursal Test")
        self.dia = DiaSemana.objects.create(dia_id=1, nombre_dia="Lunes")
        self.horario = _horario("Turno Test")
        self.empleado = _empleado(2001, nombre="ConHorario")
        # Asignación previa que DEBE conservarse ante un input inválido.
        AsignacionHorario.objects.create(
            empleado=self.empleado,
            sucursal=self.sucursal,
            horario=self.horario,
            dia_especifico=self.dia,
            hora_entrada_especifica=self.horario.hora_entrada,
            hora_salida_especifica=self.horario.hora_salida,
        )

    def _post(self, sucursales, horarios, dias):
        self.client.force_login(self.admin)
        return self.client.post(
            reverse("editar-empleado", args=[self.empleado.empleado_id]),
            data={
                "sucursales[]": sucursales,
                "horarios[]": horarios,
                "dias[]": dias,
            },
        )

    def _count(self):
        return AsignacionHorario.objects.filter(empleado=self.empleado).count()

    def test_horario_inexistente_no_borra_asignaciones(self):
        antes = self._count()
        resp = self._post([str(self.sucursal.pk)], ["999999"], [str(self.dia.pk)])
        # La vista captura el ValidationError y redirige; el empleado conserva su horario.
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self._count(), antes)

    def test_listas_desiguales_no_borra(self):
        antes = self._count()
        # Truncamiento silencioso de zip(): antes se aceptaba; ahora se rechaza.
        resp = self._post(
            [str(self.sucursal.pk), str(self.sucursal.pk)],
            [str(self.horario.pk)],
            [str(self.dia.pk), str(self.dia.pk)],
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self._count(), antes)

    def test_edicion_exitosa_recrea_asignaciones(self):
        self.assertEqual(self._count(), 1)
        resp = self._post(
            [str(self.sucursal.pk)], [str(self.horario.pk)], [str(self.dia.pk)]
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self._count(), 1)  # la anterior se reemplazó, no se duplicó


# --------------------------------------------------------------------------
# H3 — Borrado de horario autorizado y sin daño colateral
# --------------------------------------------------------------------------
class BorradoHorarioTest(TestCase):
    def setUp(self):
        self.admin = _admin()
        self.manager = _manager()
        self.sucursal = Sucursal.objects.create(nombre_sucursal="Suc H3")
        self.dia = DiaSemana.objects.create(dia_id=2, nombre_dia="Martes")
        self.horario_libre = _horario("Libre")
        self.horario_referenciado = _horario("Compartido")
        self.empleado_otro = _empleado(3001, nombre="Otro")
        # Asignación de OTRO empleado que referencia el horario compartido.
        AsignacionHorario.objects.create(
            empleado=self.empleado_otro,
            sucursal=self.sucursal,
            horario=self.horario_referenciado,
            dia_especifico=self.dia,
        )

    def test_manager_no_puede_borrar(self):
        self.client.force_login(self.manager)
        resp = self.client.delete(
            reverse("api_eliminar_horario", args=[self.horario_libre.pk])
        )
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Horario.objects.filter(pk=self.horario_libre.pk).exists())

    def test_borrado_referenciado_rechazado(self):
        self.client.force_login(self.admin)
        resp = self.client.delete(
            reverse("api_eliminar_horario", args=[self.horario_referenciado.pk])
        )
        self.assertEqual(resp.status_code, 409)
        # El horario sigue existiendo y la asignación ajena NO quedó con horario=NULL.
        self.assertTrue(Horario.objects.filter(pk=self.horario_referenciado.pk).exists())
        asign = AsignacionHorario.objects.get(
            empleado=self.empleado_otro, sucursal=self.sucursal
        )
        self.assertEqual(asign.horario_id, self.horario_referenciado.pk)

    def test_borrado_no_referenciado_admin_ok(self):
        self.client.force_login(self.admin)
        resp = self.client.delete(
            reverse("api_eliminar_horario", args=[self.horario_libre.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Horario.objects.filter(pk=self.horario_libre.pk).exists())
