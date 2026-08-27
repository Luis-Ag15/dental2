from django.db import models
from django.conf import settings
from core.encrypted_fields import EncryptedCharField, EncryptedTextField

class Cita(models.Model):

    class EstadoCita(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        CANCELADA = 'CANCELADA', 'Cancelada'
        ATENDIDA = 'ATENDIDA', 'Atendida'
        NO_ASISTIO = 'NO_ASISTIO', 'No Asistió'

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='citas')
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    estado = models.CharField(max_length=20, choices=EstadoCita.choices, default=EstadoCita.PENDIENTE)
    motivo = EncryptedTextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        # unique_together removed: the DB constraint blocked re-booking a slot
        # that had a prior CANCELADA cita. Uniqueness among active appointments
        # is enforced at the service layer (DisponibilidadService) by filtering
        # only PENDIENTE / CONFIRMADA states.
        ordering = ['fecha', 'hora_inicio']
    
    def __str__(self):
        return f"{self.usuario.email} - {self.fecha} {self.hora_inicio}"

class BloqueoHorario(models.Model):
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    motivo = EncryptedCharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['fecha', 'hora_inicio']
        ordering = ['fecha', 'hora_inicio']
    
    def __str__(self):
        return f"Bloqueo {self.fecha} {self.hora_inicio}-{self.hora_fin}"
