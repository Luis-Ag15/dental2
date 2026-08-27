from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from .forms import RegistroForm, LoginForm
from .models import User
from .tokens import email_verification_token

def registro(request):
    if request.user.is_authenticated:
        return redirect('core:index')
    
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Enviar email de confirmación
            token = email_verification_token.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            confirm_url = request.build_absolute_uri(
                reverse_lazy('usuarios:confirmar_email', kwargs={'uidb64': uid, 'token': token})
            )
            
            subject = 'Confirma tu correo electrónico'
            html_message = render_to_string('usuarios/email_confirmacion.html', {
                'user': user,
                'confirm_url': confirm_url,
            })
            plain_message = (
                f"Hola {user.nombre},\n\n"
                f"Gracias por registrarte en Dental Clinic.\n"
                f"Confirma tu correo visitando el siguiente enlace:\n\n"
                f"{confirm_url}\n\n"
                f"Si no solicitaste este registro, ignora este mensaje.\n\n"
                f"Dental Clinic"
            )
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
            )
            
            messages.success(request, '¡Registro exitoso! Por favor, confirma tu correo electrónico.')
            return redirect('usuarios:login')
    else:
        form = RegistroForm()
    
    return render(request, 'usuarios/registro.html', {'form': form})

def confirmar_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and email_verification_token.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, '¡Correo confirmado! Ya puedes iniciar sesión.')
        return redirect('usuarios:login')
    else:
        messages.error(request, 'El enlace de confirmación es inválido o ha expirado.')
        return redirect('core:index')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:index')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)
            messages.success(request, f"¡Hola de nuevo, {user.nombre}!")
            next_url = request.GET.get('next') or request.POST.get('next') or 'core:index'
            return redirect(next_url)
    else:
        form = LoginForm()
    
    return render(request, 'usuarios/login.html', {'form': form})

@login_required
@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión exitosamente.')
    return redirect('core:index')

class CustomPasswordResetView(PasswordResetView):
    template_name = 'usuarios/recuperar_password.html'
    email_template_name = 'usuarios/email_recuperacion.html'
    success_url = reverse_lazy('usuarios:login')

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'usuarios/restablecer_password.html'
    success_url = reverse_lazy('usuarios:login')
