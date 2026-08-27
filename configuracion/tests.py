from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import ConfiguracionConsultorio, HorarioDia
from .forms import HorarioDiaForm

User = get_user_model()

class ConfiguracionTests(TestCase):

    def setUp(self):
        self.staff_user = User.objects.create_user(
            email='staff@ejemplo.com',
            password='password123',
            nombre='Dr. Admin',
            telefono='1234567890',
            is_active=True,
            is_staff=True
        )
        self.normal_user = User.objects.create_user(
            email='paciente@ejemplo.com',
            password='password123',
            nombre='Paciente',
            telefono='0987654321',
            is_active=True
        )

    def test_get_config_crea_singleton_y_7_dias(self):
        config = ConfiguracionConsultorio.get_config()
        self.assertEqual(ConfiguracionConsultorio.objects.count(), 1)
        self.assertEqual(config.horarios.count(), 7)

    def test_no_staff_no_puede_acceder(self):
        self.client.login(email='paciente@ejemplo.com', password='password123')
        response = self.client.get(reverse('configuracion:configuracion'))
        self.assertEqual(response.status_code, 302)

    def test_staff_accede_configuracion(self):
        self.client.login(email='staff@ejemplo.com', password='password123')
        response = self.client.get(reverse('configuracion:configuracion'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'configuracion/configuracion.html')

    def test_validacion_hora_cierre_posterior_a_apertura(self):
        form_invalido = HorarioDiaForm(data={
            'activo': True,
            'hora_apertura': '18:00',
            'hora_cierre': '09:00'
        })
        self.assertFalse(form_invalido.is_valid())
        self.assertIn('hora_cierre', form_invalido.errors)

        form_valido = HorarioDiaForm(data={
            'activo': True,
            'hora_apertura': '09:00',
            'hora_cierre': '18:00'
        })
        self.assertTrue(form_valido.is_valid())
