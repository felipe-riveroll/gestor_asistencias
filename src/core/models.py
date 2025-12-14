# core/models.py
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone # ⬅️ Necesario para Soft Delete

# ===============================================
# 🚀 1. SOFT DELETE MANAGER (Filtra registros eliminados)
# ===============================================
class SoftDeleteManager(models.Manager):
    """Manager que devuelve SOLO los empleados activos (is_deleted=False)."""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


# ---------------------------------------------------------
#   MODELO EMPLEADO (con Soft Delete)
# ---------------------------------------------------------
class Empleado(models.Model):
    empleado_id = models.AutoField(primary_key=True, db_column='empleado_id')
    codigo_frappe = models.SmallIntegerField(unique=True, db_column='codigo_frappe')
    codigo_checador = models.SmallIntegerField(unique=True, db_column='codigo_checador')
    nombre = models.CharField(max_length=100, db_column='nombre')
    apellido_paterno = models.CharField(max_length=100, db_column='apellido_paterno')
    apellido_materno = models.CharField(max_length=100, null=True, blank=True, db_column='apellido_materno')
    email = models.EmailField(unique=True, null=True, blank=True, db_column='email')
    tiene_horario_asignado = models.BooleanField(default=False, db_column='tiene_horario_asignado')

    # Relación con Django User (opcional)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

    # ---------- 🔥 SOFT DELETE  ----------
    is_deleted = models.BooleanField(default=False, db_column='is_deleted')
    deleted_at = models.DateTimeField(null=True, blank=True, db_column='deleted_at')
    deleted_by = models.CharField(max_length=150, null=True, blank=True, db_column='deleted_by')

    # 🔑 ASIGNACIÓN DEL MANAGER (Filtro Global)
    objects = SoftDeleteManager() 
    all_objects = models.Manager() # Manager para ver TODOS los registros (incluidos eliminados)

    # 🔑 MÉTODO DELETE SOBREESCRITO (Para que .delete() marque, no borre)
    def delete(self, user=None, *args, **kwargs):
        """Realiza una eliminación lógica (soft delete)."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if user and hasattr(user, 'username'):
            self.deleted_by = user.username
        self.save()

    def undelete(self):
        """Restaura un registro eliminado lógicamente."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()

    def __str__(self):
        return f"{self.nombre} {self.apellido_paterno}"

    class Meta:
        db_table = 'Empleados'

# ---------------------------------------------------------
#   SUCURSAL, TIPO DE TURNO, HORARIO, DÍA DE LA SEMANA, ASIGNACIÓN DE HORARIO, VISTAS...
#   (Mantienen la estructura original)
# ---------------------------------------------------------

class Sucursal(models.Model):
    sucursal_id = models.AutoField(primary_key=True, db_column='sucursal_id')
    nombre_sucursal = models.CharField(max_length=100, unique=True, db_column='nombre_sucursal')
    class Meta:
        db_table = 'Sucursales'
    def __str__(self):
        return self.nombre_sucursal

class TipoTurno(models.Model):
    tipo_turno_id = models.AutoField(primary_key=True, db_column='tipo_turno_id')
    descripcion = models.CharField(max_length=100, unique=True, db_column='descripcion')
    class Meta:
        db_table = 'TipoTurno'

class Horario(models.Model):
    horario_id = models.AutoField(primary_key=True, db_column='horario_id')
    hora_entrada = models.TimeField(db_column='hora_entrada')
    hora_salida = models.TimeField(db_column='hora_salida')
    cruza_medianoche = models.BooleanField(default=False, db_column='cruza_medianoche')
    descripcion_horario = models.CharField(max_length=100, unique=True, db_column='descripcion_horario')
    class Meta:
        db_table = 'Horario'

class DiaSemana(models.Model):
    dia_id = models.IntegerField(primary_key=True, db_column='dia_id')
    nombre_dia = models.CharField(max_length=20, unique=True, db_column='nombre_dia')
    class Meta:
        db_table = 'DiaSemana'

class AsignacionHorario(models.Model):
    asignacion_id = models.AutoField(primary_key=True, db_column='asignacion_id')
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, db_column='empleado_id', related_name='asignaciones')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, db_column='sucursal_id', related_name='asignaciones')
    tipo_turno = models.ForeignKey(TipoTurno, on_delete=models.SET_NULL, null=True, blank=True, db_column='tipo_turno_id', related_name='asignaciones')
    horario = models.ForeignKey(Horario, on_delete=models.SET_NULL, null=True, blank=True, db_column='horario_id', related_name='asignaciones')
    es_primera_quincena = models.BooleanField(null=True, blank=True, db_column='es_primera_quincena')
    dia_especifico = models.ForeignKey(DiaSemana, on_delete=models.SET_NULL, null=True, blank=True, db_column='dia_especifico_id', related_name='asignaciones')
    hora_entrada_especifica = models.TimeField(null=True, blank=True, db_column='hora_entrada_especifica')
    hora_salida_especifica = models.TimeField(null=True, blank=True, db_column='hora_salida_especifica')
    hora_salida_especifica_cruza_medianoche = models.BooleanField(default=False, db_column='hora_salida_especifica_cruza_medianoche')
    comentarios = models.CharField(max_length=255, null=True, blank=True, db_column='comentarios')
    class Meta:
        db_table = 'AsignacionHorario'
        unique_together = (('empleado', 'sucursal', 'dia_especifico', 'es_primera_quincena'),)
        indexes = [
            models.Index(fields=['empleado', 'dia_especifico']),
            models.Index(fields=['empleado', 'sucursal']),
            models.Index(fields=['horario']),
            models.Index(fields=['tipo_turno']),
            models.Index(fields=['dia_especifico']),
        ]
    # --- AGREGA todo ESTE BLOQUE AQUÍ ---
    def _str_(self):
        # 1. Obtenemos las horas correctas
        if self.hora_entrada_especifica:
            inicio = self.hora_entrada_especifica
            fin = self.hora_salida_especifica
        elif self.horario:
            inicio = self.horario.hora_entrada
            fin = self.horario.hora_salida
        else:
            return "Horario indefinido"

        # Formateamos bonito (quitamos segundos extra si no son necesarios)
        txt_inicio = inicio.strftime('%H:%M') if inicio else "??"
        txt_fin = fin.strftime('%H:%M') if fin else "??"
        
        texto_base = f"{txt_inicio} - {txt_fin}"

        # 2. Si tiene comentario, lo ponemos. Si no, devolvemos solo la hora.
        if self.comentarios and self.comentarios.strip():
            return f"{texto_base} ({self.comentarios})"
        
        return texto_base

class ResumenHorario(models.Model):
    empleado_id = models.IntegerField(primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=100)
    nombre_sucursal = models.CharField(max_length=100, null=True)
    dia_especifico_id = models.IntegerField(null=True)
    horario = models.CharField(max_length=100, null=True)
    class Meta:
        db_table = 'vista_resumen_horarios'
        managed = False

class TablaHorarios(models.Model):
    codigo_frappe = models.SmallIntegerField()
    nombre_completo = models.CharField(max_length=200)
    nombre_sucursal = models.CharField(max_length=100)
    Lunes = models.JSONField(null=True)
    Martes = models.JSONField(null=True)
    Miércoles = models.JSONField(null=True, db_column="Miércoles")
    Jueves = models.JSONField(null=True)
    Viernes = models.JSONField(null=True)
    Sábado = models.JSONField(null=True)
    Domingo = models.JSONField(null=True)
    class Meta:
        managed = False
        db_table = None