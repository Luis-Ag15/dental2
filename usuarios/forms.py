from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import password_validation
from django.core.validators import EmailValidator
from .models import User

class RegistroForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254,
        validators=[EmailValidator()],
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'})
    )
    nombre = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre completo'})
    )
    telefono = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}),
        help_text=password_validation.password_validators_help_text_html()
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar contraseña'})
    )
    
    class Meta:
        model = User
        fields = ('email', 'nombre', 'telefono', 'password1', 'password2')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este correo electrónico ya está registrado.')
        return email
    
    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if not telefono.isdigit() or len(telefono) < 10:
            raise forms.ValidationError('Ingrese un número de teléfono válido.')
        return telefono
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False
        if commit:
            user.save()
        return user

import time
import math
from django.core.cache import cache

MAX_LOGIN_ATTEMPTS = 3
LOCKOUT_DURATION_SECONDS = 900  # 15 minutos
ATTEMPTS_EXPIRY_SECONDS = 900   # 15 minutos de inactividad


def get_login_cache_keys(email):
    normalized_email = email.lower().strip()
    return (
        f"login_attempts_{normalized_email}",
        f"login_lockout_{normalized_email}"
    )


def clear_login_attempts(email):
    attempts_key, lockout_key = get_login_cache_keys(email)
    cache.delete(attempts_key)
    cache.delete(lockout_key)


class LoginForm(forms.Form):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico', 'autofocus': True}),
        label="Correo electrónico"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}),
        label="Contraseña"
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if email and password:
            attempts_key, lockout_key = get_login_cache_keys(email)

            # 1. Verificar si la cuenta/correo está actualmente bloqueada
            lockout_until = cache.get(lockout_key)
            if lockout_until:
                remaining_seconds = max(1, int(lockout_until - time.time()))
                remaining_minutes = math.ceil(remaining_seconds / 60)
                min_str = f"{remaining_minutes} minutos" if remaining_minutes > 1 else "1 minuto"
                raise forms.ValidationError(
                    f"Has superado el límite de 3 intentos fallidos. Tu acceso está bloqueado temporalmente. Inténtalo de nuevo en {min_str} o restablece tu contraseña."
                )

            # 2. Validar credenciales
            user = None
            try:
                user_candidate = User.objects.get(email=email)
                if user_candidate.check_password(password):
                    user = user_candidate
            except User.DoesNotExist:
                user = None

            if user is None:
                # Incrementar contador de intentos fallidos
                current_attempts = cache.get(attempts_key, 0) + 1
                if current_attempts >= MAX_LOGIN_ATTEMPTS:
                    lockout_until_ts = time.time() + LOCKOUT_DURATION_SECONDS
                    cache.set(lockout_key, lockout_until_ts, timeout=LOCKOUT_DURATION_SECONDS)
                    cache.delete(attempts_key)
                    raise forms.ValidationError(
                        "Has superado el límite de 3 intentos fallidos. Tu acceso ha sido bloqueado temporalmente por 15 minutos por motivos de seguridad."
                    )
                else:
                    cache.set(attempts_key, current_attempts, timeout=ATTEMPTS_EXPIRY_SECONDS)
                    remaining_attempts = MAX_LOGIN_ATTEMPTS - current_attempts
                    if remaining_attempts == 1:
                        raise forms.ValidationError(
                            "Correo electrónico o contraseña incorrectos. Te queda 1 intento antes de que la cuenta sea bloqueada temporalmente."
                        )
                    else:
                        raise forms.ValidationError(
                            f"Correo electrónico o contraseña incorrectos. Te quedan {remaining_attempts} intentos antes de que la cuenta sea bloqueada temporalmente."
                        )

            if not user.is_active:
                raise forms.ValidationError("Tu cuenta no está activada. Revisa tu correo electrónico para confirmar tu cuenta antes de iniciar sesión.")

            # Credenciales correctas y usuario activo -> reiniciar intentos
            clear_login_attempts(email)
            cleaned_data['user'] = user

        return cleaned_data
