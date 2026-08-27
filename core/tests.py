from django.test import TestCase
from django.urls import reverse
from django.db import connection
from datetime import date, time
from core.encryption import encrypt, decrypt
from usuarios.models import User
from citas.models import Cita, BloqueoHorario


class CoreViewsTests(TestCase):
    
    def test_pagina_inicio(self):
        response = self.client.get(reverse('core:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/index.html')

    def test_pagina_servicios(self):
        response = self.client.get(reverse('core:servicios'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/servicios.html')

    def test_pagina_contacto(self):
        response = self.client.get(reverse('core:contacto'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/contacto.html')

    def test_pagina_terminos(self):
        response = self.client.get(reverse('core:terminos'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/terminos.html')
        self.assertContains(response, 'Términos y Condiciones')

    def test_pagina_privacidad(self):
        response = self.client.get(reverse('core:privacidad'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/privacidad.html')
        self.assertContains(response, 'Política de Privacidad')


class EncryptionUnitTests(TestCase):
    """Pruebas unitarias para el módulo central de cifrado Fernet."""

    def test_encrypt_decrypt_roundtrip(self):
        texto = 'Información médica confidencial del paciente'
        cifrado = encrypt(texto)
        self.assertNotEqual(cifrado, texto)
        self.assertTrue(cifrado.startswith('gAAAAA'))
        self.assertEqual(decrypt(cifrado), texto)

    def test_encrypt_empty_and_none(self):
        self.assertEqual(encrypt(''), '')
        self.assertIsNone(encrypt(None))
        self.assertEqual(decrypt(''), '')
        self.assertIsNone(decrypt(None))

    def test_decrypt_plaintext_fallback(self):
        texto_plano = 'texto previo no cifrado'
        self.assertEqual(decrypt(texto_plano), texto_plano)

    def test_iv_aleatorio_produce_diferentes_cifrados(self):
        texto = 'mismo motivo de consulta'
        c1 = encrypt(texto)
        c2 = encrypt(texto)
        self.assertNotEqual(c1, c2)
        self.assertEqual(decrypt(c1), texto)
        self.assertEqual(decrypt(c2), texto)


class EncryptedModelsIntegrationTests(TestCase):
    """Pruebas de integración para verificar el cifrado transparente en BD."""

    def test_usuario_nombre_y_telefono_cifrados_en_bd(self):
        user = User.objects.create_user(
            email='paciente@test.com',
            password='Password123!',
            nombre='Carlos Santana',
            telefono='5512345678'
        )

        # A través del ORM, se lee descifrado automáticamente
        user_db = User.objects.get(id=user.id)
        self.assertEqual(user_db.nombre, 'Carlos Santana')
        self.assertEqual(user_db.telefono, '5512345678')

        # Consultando el valor crudo en la base de datos SQL
        with connection.cursor() as cursor:
            cursor.execute("SELECT nombre, telefono FROM usuarios_user WHERE id = %s", [user.id])
            raw_nombre, raw_telefono = cursor.fetchone()

        self.assertTrue(raw_nombre.startswith('gAAAAA'))
        self.assertTrue(raw_telefono.startswith('gAAAAA'))
        self.assertEqual(decrypt(raw_nombre), 'Carlos Santana')
        self.assertEqual(decrypt(raw_telefono), '5512345678')

    def test_cita_motivo_cifrado_en_bd(self):
        user = User.objects.create_user(
            email='cita_test@test.com',
            password='Password123!',
            nombre='Ana Gomez',
            telefono='5587654321'
        )
        cita = Cita.objects.create(
            usuario=user,
            fecha=date.today(),
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0),
            motivo='Dolor agudo en tercer molar inferior izquierdo'
        )

        # Lectura ORM
        cita_db = Cita.objects.get(id=cita.id)
        self.assertEqual(cita_db.motivo, 'Dolor agudo en tercer molar inferior izquierdo')

        # Verificación directa en base de datos
        with connection.cursor() as cursor:
            cursor.execute("SELECT motivo FROM citas_cita WHERE id = %s", [cita.id])
            raw_motivo = cursor.fetchone()[0]

        self.assertTrue(raw_motivo.startswith('gAAAAA'))
        self.assertEqual(decrypt(raw_motivo), 'Dolor agudo en tercer molar inferior izquierdo')

    def test_bloqueo_horario_motivo_cifrado_en_bd(self):
        bloqueo = BloqueoHorario.objects.create(
            fecha=date.today(),
            hora_inicio=time(14, 0),
            hora_fin=time(15, 0),
            motivo='Mantenimiento de equipo de rayos X'
        )

        bloqueo_db = BloqueoHorario.objects.get(id=bloqueo.id)
        self.assertEqual(bloqueo_db.motivo, 'Mantenimiento de equipo de rayos X')

        with connection.cursor() as cursor:
            cursor.execute("SELECT motivo FROM citas_bloqueohorario WHERE id = %s", [bloqueo.id])
            raw_motivo = cursor.fetchone()[0]

        self.assertTrue(raw_motivo.startswith('gAAAAA'))
        self.assertEqual(decrypt(raw_motivo), 'Mantenimiento de equipo de rayos X')
