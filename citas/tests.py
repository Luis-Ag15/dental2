from datetime import time, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from configuracion.models import ConfiguracionConsultorio
from .models import Cita, BloqueoHorario
from .services import DisponibilidadService

User = get_user_model()

class CitaTests(TestCase):
    
    def setUp(self):
        ConfiguracionConsultorio.get_config()
        self.user = User.objects.create_user(
            email='test@ejemplo.com',
            password='password123',
            nombre='Test User',
            telefono='1234567890',
            is_active=True
        )
        self.staff_user = User.objects.create_user(
            email='doctor@ejemplo.com',
            password='password123',
            nombre='Dr. General',
            telefono='1122334455',
            is_active=True,
            is_staff=True
        )
        self.client.login(email='test@ejemplo.com', password='password123')

    def _get_proximo_dia_laboral(self):
        """Retorna una fecha futura garantizada en día laboral (lunes a viernes)."""
        dias = 1
        fecha = timezone.now().date() + timedelta(days=dias)
        while fecha.weekday() >= 5:
            dias += 1
            fecha = timezone.now().date() + timedelta(days=dias)
        return fecha

    def test_crear_cita_exitosa(self):
        fecha = self._get_proximo_dia_laboral()
        response = self.client.post(reverse('citas:agendar'), {
            'fecha': fecha.strftime('%Y-%m-%d'),
            'hora': '10:00',
            'motivo': 'Consulta general / Revisión'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Cita.objects.count(), 1)
        cita = Cita.objects.first()
        self.assertEqual(cita.usuario, self.user)
        self.assertEqual(cita.estado, Cita.EstadoCita.PENDIENTE)

    def test_no_permitir_fecha_pasada(self):
        fecha = timezone.now().date() - timedelta(days=1)
        response = self.client.get(reverse('citas:agendar'), {'fecha': fecha.strftime('%Y-%m-%d')})
        self.assertEqual(response.status_code, 200)

    def test_usuario_solo_ve_sus_citas(self):
        otro_user = User.objects.create_user(
            email='otro@ejemplo.com',
            password='password123',
            nombre='Otro User',
            telefono='0987654321',
            is_active=True
        )
        fecha = self._get_proximo_dia_laboral()
        cita1 = Cita.objects.create(
            usuario=self.user,
            fecha=fecha,
            hora_inicio=time(10, 0),
            hora_fin=time(10, 30),
            motivo='Consulta',
            estado=Cita.EstadoCita.PENDIENTE
        )
        cita2 = Cita.objects.create(
            usuario=otro_user,
            fecha=fecha + timedelta(days=1),
            hora_inicio=time(11, 0),
            hora_fin=time(11, 30),
            motivo='Consulta otro',
            estado=Cita.EstadoCita.PENDIENTE
        )
        response = self.client.get(reverse('citas:mis_citas'))
        self.assertEqual(response.status_code, 200)
        citas = response.context['citas_proximas']
        self.assertEqual(citas.count(), 1)
        self.assertEqual(citas.first(), cita1)

    def test_cancelar_cita_exitosa(self):
        fecha = self._get_proximo_dia_laboral()
        cita = Cita.objects.create(
            usuario=self.user,
            fecha=fecha,
            hora_inicio=time(10, 0),
            hora_fin=time(10, 30),
            motivo='Consulta a cancelar',
            estado=Cita.EstadoCita.PENDIENTE
        )
        response = self.client.post(reverse('citas:cancelar_cita', kwargs={'cita_id': cita.id}))
        self.assertEqual(response.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.EstadoCita.CANCELADA)

    def test_no_permitir_doble_reserva_mismo_horario(self):
        fecha = self._get_proximo_dia_laboral()
        # Crear primera cita
        Cita.objects.create(
            usuario=self.user,
            fecha=fecha,
            hora_inicio=time(10, 0),
            hora_fin=time(10, 30),
            motivo='Primera cita',
            estado=Cita.EstadoCita.CONFIRMADA
        )
        # Intentar agendar en el mismo horario
        response = self.client.post(reverse('citas:agendar'), {
            'fecha': fecha.strftime('%Y-%m-%d'),
            'hora': '10:00',
            'motivo': 'Limpieza dental (Profilaxis)'
        })
        self.assertEqual(Cita.objects.count(), 1)

    def test_bloquear_horario_especifico_staff(self):
        self.client.login(email='doctor@ejemplo.com', password='password123')
        fecha = self._get_proximo_dia_laboral()
        response = self.client.post(reverse('citas:bloquear_horario'), {
            'fecha': fecha.strftime('%Y-%m-%d'),
            'tipo': 'especifico',
            'hora_inicio': '10:00',
            'hora_fin': '11:00',
            'motivo': 'Mantenimiento de sillón dental'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BloqueoHorario.objects.count(), 1)
        self.assertFalse(DisponibilidadService.verificar_disponibilidad(fecha, time(10, 0)))

    def test_bloquear_dia_completo_staff(self):
        self.client.login(email='doctor@ejemplo.com', password='password123')
        fecha = self._get_proximo_dia_laboral()
        response = self.client.post(reverse('citas:bloquear_horario'), {
            'fecha': fecha.strftime('%Y-%m-%d'),
            'tipo': 'dia_completo',
            'motivo': 'Capacitación médica'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BloqueoHorario.objects.count(), 1)
        disponibles = DisponibilidadService.get_horarios_disponibles(fecha)
        self.assertEqual(len(disponibles), 0)

    def test_cambiar_estado_cita_staff(self):
        self.client.login(email='doctor@ejemplo.com', password='password123')
        fecha = self._get_proximo_dia_laboral()
        cita = Cita.objects.create(
            usuario=self.user,
            fecha=fecha,
            hora_inicio=time(10, 0),
            hora_fin=time(10, 30),
            motivo='Consulta',
            estado=Cita.EstadoCita.PENDIENTE
        )
        response = self.client.post(reverse('citas:cambiar_estado', kwargs={'cita_id': cita.id}), {
            'estado': Cita.EstadoCita.CONFIRMADA
        })
        self.assertEqual(response.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.EstadoCita.CONFIRMADA)

    def test_no_staff_no_accede_dashboard(self):
        # Usuario normal logueado
        response = self.client.get(reverse('citas:dashboard'))
        self.assertEqual(response.status_code, 302)
