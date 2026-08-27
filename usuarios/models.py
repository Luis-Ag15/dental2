from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from core.encrypted_fields import EncryptedCharField

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El correo electrónico es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True, verbose_name='Correo electrónico')
    nombre = EncryptedCharField(max_length=100, verbose_name='Nombre completo')
    telefono = EncryptedCharField(max_length=15, verbose_name='Teléfono')
    is_active = models.BooleanField(default=False, verbose_name='Activo')
    date_joined = models.DateTimeField(default=timezone.now, verbose_name='Fecha de registro')
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'telefono']
    
    objects = CustomUserManager()
    
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='usuarios_user_set',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='usuarios_user_set',
        blank=True
    )
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return self.nombre
    
    def get_short_name(self):
        return self.nombre
