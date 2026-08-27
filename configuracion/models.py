from django.db import models


DIAS_SEMANA = [
    ('1', 'Lunes'),
    ('2', 'Martes'),
    ('3', 'Miércoles'),
    ('4', 'Jueves'),
    ('5', 'Viernes'),
    ('6', 'Sábado'),
    ('7', 'Domingo'),
]

ZONAS_HORARIAS = [
    ('America/Mexico_City', 'Ciudad de México (CST/CDT, UTC-6/UTC-5)'),
    ('America/Monterrey',   'Monterrey (CST/CDT, UTC-6/UTC-5)'),
    ('America/Tijuana',     'Tijuana (PST/PDT, UTC-8/UTC-7)'),
    ('America/Cancun',      'Cancún (EST, UTC-5)'),
    ('America/Chihuahua',   'Chihuahua (MST/MDT, UTC-7/UTC-6)'),
]


class ConfiguracionConsultorio(models.Model):
    """Modelo singleton: siempre habrá exactamente un registro."""

    nombre_consultorio = models.CharField(
        max_length=150, verbose_name='Nombre del consultorio',
        default='Dental Clinic'
    )
    nombre_dentista = models.CharField(
        max_length=200, verbose_name='Nombre del dentista',
        default='Dr. Nombre Apellido'
    )
    telefono = models.CharField(
        max_length=50, verbose_name='Teléfono',
        default='+52 55 1234 5678'
    )
    direccion = models.CharField(
        max_length=300, verbose_name='Dirección',
        default='Calle, Número, Colonia, Ciudad'
    )
    zona_horaria = models.CharField(
        max_length=50, choices=ZONAS_HORARIAS,
        default='America/Mexico_City', verbose_name='Zona horaria'
    )

    class Meta:
        verbose_name = 'Configuración del consultorio'
        verbose_name_plural = 'Configuración del consultorio'

    def __str__(self):
        return self.nombre_consultorio

    @classmethod
    def get_config(cls):
        """Devuelve la única instancia, creándola con sus 7 HorarioDia si no existe."""
        obj, created = cls.objects.get_or_create(pk=1)
        if created:
            obj._crear_horarios_default()
        return obj

    def _crear_horarios_default(self):
        """Crea las 7 filas de HorarioDia con valores por defecto."""
        defaults = {
            '1': (True,  '09:00', '18:00'),  # Lunes
            '2': (True,  '09:00', '18:00'),  # Martes
            '3': (True,  '09:00', '18:00'),  # Miércoles
            '4': (True,  '09:00', '18:00'),  # Jueves
            '5': (True,  '09:00', '15:00'),  # Viernes
            '6': (False, '09:00', '13:00'),  # Sábado  (cerrado por defecto)
            '7': (False, '09:00', '13:00'),  # Domingo (cerrado por defecto)
        }
        for dia, (activo, apertura, cierre) in defaults.items():
            HorarioDia.objects.get_or_create(
                consultorio=self, dia=dia,
                defaults={
                    'activo': activo,
                    'hora_apertura': apertura,
                    'hora_cierre': cierre,
                }
            )


class HorarioDia(models.Model):
    """Horario de atención para un día específico de la semana."""

    consultorio = models.ForeignKey(
        ConfiguracionConsultorio,
        on_delete=models.CASCADE,
        related_name='horarios',
    )
    dia = models.CharField(max_length=1, choices=DIAS_SEMANA, verbose_name='Día')
    activo = models.BooleanField(default=True, verbose_name='Día laboral')
    hora_apertura = models.TimeField(default='09:00', verbose_name='Hora de apertura')
    hora_cierre   = models.TimeField(default='18:00', verbose_name='Hora de cierre')

    class Meta:
        verbose_name = 'Horario del día'
        verbose_name_plural = 'Horarios por día'
        unique_together = ('consultorio', 'dia')
        ordering = ('dia',)

    def __str__(self):
        estado = 'Abierto' if self.activo else 'Cerrado'
        return f'{self.get_dia_display()} — {estado} {self.hora_apertura}–{self.hora_cierre}'
