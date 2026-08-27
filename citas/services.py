from datetime import datetime, timedelta, time
from django.utils import timezone
from .models import Cita, BloqueoHorario


class DisponibilidadService:
    DURACION_CITA = timedelta(minutes=30)

    @classmethod
    def _get_horario_dia(cls, fecha):
        """
        Devuelve el objeto HorarioDia activo para la fecha dada,
        leyendo la configuración desde la base de datos.
        Retorna None si el día está cerrado o no configurado.
        """
        # Importación local para evitar dependencia circular al arrancar
        from configuracion.models import ConfiguracionConsultorio
        try:
            config = ConfiguracionConsultorio.get_config()
            dia_semana = str(fecha.weekday() + 1)   # 1=Lunes … 7=Domingo
            horario = config.horarios.filter(dia=dia_semana, activo=True).first()
            return horario
        except Exception:
            return None

    @classmethod
    def get_horarios_disponibles(cls, fecha):
        """Obtiene los horarios disponibles para una fecha específica."""
        horario = cls._get_horario_dia(fecha)
        if horario is None:
            return []

        inicio = datetime.combine(fecha, horario.hora_apertura)
        fin    = datetime.combine(fecha, horario.hora_cierre)

        # Si la fecha es hoy, descartar slots cuya hora de inicio ya pasó
        hoy = timezone.localtime(timezone.now())
        if fecha == hoy.date():
            ahora = datetime.combine(fecha, hoy.time())
            while inicio + cls.DURACION_CITA <= fin and inicio <= ahora:
                inicio += cls.DURACION_CITA

        # Generar todos los slots posibles
        slots = []
        hora_actual = inicio
        while hora_actual + cls.DURACION_CITA <= fin:
            slots.append(hora_actual.time().replace(second=0, microsecond=0))
            hora_actual += cls.DURACION_CITA

        # Horarios ocupados por citas confirmadas/pendientes
        citas_ocupadas = set(
            t.replace(second=0, microsecond=0)
            for t in Cita.objects.filter(
                fecha=fecha,
                estado__in=['PENDIENTE', 'CONFIRMADA']
            ).values_list('hora_inicio', flat=True)
        )

        # Bloqueos
        bloqueos = BloqueoHorario.objects.filter(fecha=fecha)

        def slot_bloqueado(slot):
            slot_fin = (datetime.combine(fecha, slot) + cls.DURACION_CITA).time().replace(second=0, microsecond=0)
            for b in bloqueos:
                b_inicio = b.hora_inicio.replace(second=0, microsecond=0)
                b_fin    = b.hora_fin.replace(second=0, microsecond=0)
                if slot < b_fin and slot_fin > b_inicio:
                    return True
            return False

        disponibles = [
            s.strftime('%H:%M')
            for s in slots
            if s not in citas_ocupadas and not slot_bloqueado(s)
        ]

        return disponibles

    @classmethod
    def verificar_disponibilidad(cls, fecha, hora_inicio):
        """Verifica si un horario específico está disponible."""
        horarios  = cls.get_horarios_disponibles(fecha)
        hora_str  = hora_inicio.strftime('%H:%M')
        return hora_str in horarios
