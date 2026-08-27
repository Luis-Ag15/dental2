from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from usuarios.tokens import email_verification_token

User = get_user_model()

class UsuarioTests(TestCase):
    
    def test_registro_exitoso(self):
        response = self.client.post(reverse('usuarios:registro'), {
            'email': 'test@ejemplo.com',
            'nombre': 'Test User',
            'telefono': '1234567890',
            'password1': 'Contraseña123!',
            'password2': 'Contraseña123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.email, 'test@ejemplo.com')
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
    
    def test_email_duplicado(self):
        User.objects.create_user(
            email='test@ejemplo.com',
            password='password123',
            nombre='Test',
            telefono='1234567890'
        )
        response = self.client.post(reverse('usuarios:registro'), {
            'email': 'test@ejemplo.com',
            'nombre': 'Test 2',
            'telefono': '0987654321',
            'password1': 'Contraseña123!',
            'password2': 'Contraseña123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue('email' in response.context['form'].errors)
    
    def test_verificacion_email(self):
        user = User.objects.create_user(
            email='test@ejemplo.com',
            password='password123',
            nombre='Test',
            telefono='1234567890',
            is_active=False
        )
        token = email_verification_token.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        response = self.client.get(reverse('usuarios:confirmar_email', kwargs={
            'uidb64': uid,
            'token': token
        }))
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_token_invalido_para_otro_usuario(self):
        user1 = User.objects.create_user(email='u1@test.com', password='p1', nombre='U1', telefono='1111111111', is_active=False)
        user2 = User.objects.create_user(email='u2@test.com', password='p2', nombre='U2', telefono='2222222222', is_active=False)
        
        token_u1 = email_verification_token.make_token(user1)
        # Intentar validar el token de user1 contra user2
        self.assertFalse(email_verification_token.check_token(user2, token_u1))

    def test_token_se_invalida_tras_activacion(self):
        user = User.objects.create_user(email='activar@test.com', password='p1', nombre='UA', telefono='3333333333', is_active=False)
        token = email_verification_token.make_token(user)
        self.assertTrue(email_verification_token.check_token(user, token))
        
        # Una vez activado, el token anterior debe invalidarse
        user.is_active = True
        user.save()
        self.assertFalse(email_verification_token.check_token(user, token))

    def test_login_exitoso_y_fallido(self):
        user = User.objects.create_user(
            email='activo@ejemplo.com',
            password='password123',
            nombre='Usuario Activo',
            telefono='1234567890',
            is_active=True
        )
        # Login con contraseña errónea
        res_bad = self.client.post(reverse('usuarios:login'), {
            'username': 'activo@ejemplo.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(res_bad.status_code, 200)

        # Login correcto
        res_ok = self.client.post(reverse('usuarios:login'), {
            'username': 'activo@ejemplo.com',
            'password': 'password123'
        })
        self.assertEqual(res_ok.status_code, 302)

    def test_usuario_inactivo_no_puede_iniciar_sesion(self):
        User.objects.create_user(
            email='inactivo@ejemplo.com',
            password='password123',
            nombre='Usuario Inactivo',
            telefono='1234567890',
            is_active=False
        )
        response = self.client.post(reverse('usuarios:login'), {
            'username': 'inactivo@ejemplo.com',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 200)

    def test_limite_3_intentos_fallidos_y_bloqueo(self):
        User.objects.create_user(
            email='limite@ejemplo.com',
            password='password123',
            nombre='Usuario Limite',
            telefono='1234567890',
            is_active=True
        )

        # Intento 1 fallido: quedan 2 intentos
        res1 = self.client.post(reverse('usuarios:login'), {
            'username': 'limite@ejemplo.com',
            'password': 'badpassword1'
        })
        self.assertEqual(res1.status_code, 200)
        self.assertContains(res1, 'Te quedan 2 intentos')

        # Intento 2 fallido: queda 1 intento
        res2 = self.client.post(reverse('usuarios:login'), {
            'username': 'limite@ejemplo.com',
            'password': 'badpassword2'
        })
        self.assertEqual(res2.status_code, 200)
        self.assertContains(res2, 'Te queda 1 intento')

        # Intento 3 fallido: se activa el bloqueo
        res3 = self.client.post(reverse('usuarios:login'), {
            'username': 'limite@ejemplo.com',
            'password': 'badpassword3'
        })
        self.assertEqual(res3.status_code, 200)
        self.assertContains(res3, 'Has superado el límite de 3 intentos fallidos')

        # Intento 4 (incluso con contraseña correcta): permanece bloqueado
        res4 = self.client.post(reverse('usuarios:login'), {
            'username': 'limite@ejemplo.com',
            'password': 'password123'
        })
        self.assertEqual(res4.status_code, 200)
        self.assertContains(res4, 'bloqueado temporalmente')

    def test_login_exitoso_reinicia_contador_intentos(self):
        User.objects.create_user(
            email='reset@ejemplo.com',
            password='password123',
            nombre='Usuario Reset',
            telefono='1234567890',
            is_active=True
        )

        # 2 intentos fallidos
        self.client.post(reverse('usuarios:login'), {'username': 'reset@ejemplo.com', 'password': 'bad'})
        self.client.post(reverse('usuarios:login'), {'username': 'reset@ejemplo.com', 'password': 'bad'})

        # 3er intento exitoso -> debe iniciar sesión y limpiar el contador
        res_ok = self.client.post(reverse('usuarios:login'), {'username': 'reset@ejemplo.com', 'password': 'password123'})
        self.assertEqual(res_ok.status_code, 302)

        # Cierra sesión y luego falla 1 vez -> debe tener de nuevo 2 intentos restantes
        self.client.logout()
        res_after = self.client.post(reverse('usuarios:login'), {'username': 'reset@ejemplo.com', 'password': 'bad'})
        self.assertEqual(res_after.status_code, 200)
        self.assertContains(res_after, 'Te quedan 2 intentos')

    def test_logout_requiere_post(self):
        user = User.objects.create_user(
            email='user@ejemplo.com',
            password='password123',
            nombre='User',
            telefono='1234567890',
            is_active=True
        )
        self.client.login(email='user@ejemplo.com', password='password123')
        # GET debería ser rechazado (405 Method Not Allowed)
        res_get = self.client.get(reverse('usuarios:logout'))
        self.assertEqual(res_get.status_code, 405)

        # POST cierra sesión exitosamente
        res_post = self.client.post(reverse('usuarios:logout'))
        self.assertEqual(res_post.status_code, 302)
