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
            try:
                user = User.objects.get(email=email)
                if not user.check_password(password):
                    raise forms.ValidationError("Correo electrónico o contraseña incorrectos.")
                if not user.is_active:
                    raise forms.ValidationError("Tu cuenta no está activada. Revisa tu correo electrónico para confirmar tu cuenta antes de iniciar sesión.")
                cleaned_data['user'] = user
            except User.DoesNotExist:
                raise forms.ValidationError("Correo electrónico o contraseña incorrectos.")

        return cleaned_data
