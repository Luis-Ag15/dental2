import json
import logging
from datetime import datetime
from django.db import IntegrityError
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from configuracion.models import ConfiguracionConsultorio
from .models import Cita, BloqueoHorario
from .forms import AgendarCitaForm
from .services import DisponibilidadService

logger = logging.getLogger(__name__)


def enviar_email_confirmacion_cita(cita, request=None):
    """
    Envía un correo electrónico al paciente cuando el dentista confirma su cita.
    """
    try:
        config = ConfiguracionConsultorio.get_config()
    except Exception:
        config = None

    nombre_consultorio = config.nombre_consultorio if config else "Dental Clinic"
    nombre_dentista = config.nombre_dentista if config else "Especialista Odontológico"
    direccion = config.direccion if config else ""
    telefono = config.telefono if config else ""

    MESES_ES = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    DIAS_ES = {
        0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves',
        4: 'Viernes', 5: 'Sábado', 6: 'Domingo'
    }
    dia_nombre = DIAS_ES.get(cita.fecha.weekday(), '')
    mes_nombre = MESES_ES.get(cita.fecha.month, '')
    fecha_formateada = f"{dia_nombre} {cita.fecha.day} de {mes_nombre} de {cita.fecha.year}"

    if request:
        mis_citas_url = request.build_absolute_uri(reverse('citas:mis_citas'))
    else:
        mis_citas_url = reverse('citas:mis_citas')

    asunto = f"¡Cita Confirmada! - {nombre_consultorio}"

    contexto = {
        'cita': cita,
        'config': config,
        'nombre_consultorio': nombre_consultorio,
        'nombre_dentista': nombre_dentista,
        'direccion': direccion,
        'telefono': telefono,
        'fecha_formateada': fecha_formateada,
        'mis_citas_url': mis_citas_url,
    }

    html_message = render_to_string('citas/email_cita_confirmada.html', contexto)
    plain_message = (
        f"Hola {cita.usuario.nombre},\n\n"
        f"¡Tu cita en {nombre_consultorio} ha sido CONFIRMADA con éxito!\n\n"
        f"--- DETALLES DE TU CITA ---\n"
        f"• Fecha: {fecha_formateada}\n"
        f"• Horario: {cita.hora_inicio.strftime('%H:%M')} - {cita.hora_fin.strftime('%H:%M')}\n"
        f"• Motivo: {cita.motivo}\n"
        f"• Especialista: {nombre_dentista}\n"
        f"• Consultorio: {nombre_consultorio}\n"
        f"• Dirección: {direccion}\n"
        f"• Teléfono: {telefono}\n\n"
        f"Puedes revisar tus citas programadas en: {mis_citas_url}\n\n"
        f"Recomendación: Te sugerimos llegar 10 minutos antes de tu cita.\n\n"
        f"Saludos cordiales,\n"
        f"{nombre_consultorio}"
    )

    try:
        send_mail(
            asunto,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [cita.usuario.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Error enviando correo de confirmación de cita {cita.id} a {cita.usuario.email}: {e}")
        return False


@login_required
def agendar_cita(request):
    # Verificar si el usuario tiene email confirmado
    if not request.user.is_active:
        messages.error(request, 'Debes confirmar tu correo electrónico para agendar una cita.')
        return redirect('core:index')
    
    horarios_disponibles = []
    fecha_seleccionada = request.GET.get('fecha')
    
    if request.method == 'POST':
        # Cargar horarios de la fecha enviada en el POST para validar el campo hora
        fecha_post = request.POST.get('fecha')
        if fecha_post:
            try:
                fecha_obj = timezone.datetime.strptime(fecha_post, '%Y-%m-%d').date()
                if fecha_obj >= timezone.now().date():
                    horarios_disponibles = DisponibilidadService.get_horarios_disponibles(fecha_obj)
            except ValueError:
                pass

        form = AgendarCitaForm(request.POST, horarios_disponibles=horarios_disponibles)
        if form.is_valid():
            fecha = form.cleaned_data['fecha']
            hora_str = form.cleaned_data['hora']
            hora_inicio = timezone.datetime.strptime(hora_str, '%H:%M').time()
            motivo = form.cleaned_data['motivo']
            
            # Verificar disponibilidad con transacción
            try:
                with transaction.atomic():
                    if DisponibilidadService.verificar_disponibilidad(fecha, hora_inicio):
                        hora_fin = (datetime.combine(fecha, hora_inicio) + 
                                   DisponibilidadService.DURACION_CITA).time()
                        
                        cita = Cita.objects.create(
                            usuario=request.user,
                            fecha=fecha,
                            hora_inicio=hora_inicio,
                            hora_fin=hora_fin,
                            motivo=motivo,
                            estado=Cita.EstadoCita.PENDIENTE
                        )
                        messages.success(request, f'¡Cita agendada exitosamente para el {fecha} a las {hora_str}!')
                        return redirect('citas:confirmacion', cita_id=cita.id)
                    else:
                        messages.error(request, 'El horario seleccionado ya no está disponible.')
            except IntegrityError:
                # Race condition: another request claimed this slot between our
                # availability check and the INSERT. Treat it as unavailable.
                messages.error(request, 'El horario seleccionado ya no está disponible. Por favor elige otro.')
        else:
            messages.error(request, 'Por favor, corrige los errores del formulario.')
    else:
        # Si GET, obtener horarios disponibles para fecha seleccionada
        if fecha_seleccionada:
            try:
                fecha = timezone.datetime.strptime(fecha_seleccionada, '%Y-%m-%d').date()
                if fecha >= timezone.now().date():
                    horarios_disponibles = DisponibilidadService.get_horarios_disponibles(fecha)
            except ValueError:
                pass
        
        form = AgendarCitaForm(horarios_disponibles=horarios_disponibles)
    
    return render(request, 'citas/agendar.html', {
        'form': form,
        'horarios_disponibles': horarios_disponibles,
        'fecha_seleccionada': fecha_seleccionada,
    })

@login_required
def mis_citas(request):
    citas = Cita.objects.filter(usuario=request.user)
    citas_proximas = citas.filter(
        fecha__gte=timezone.now().date(),
        estado__in=['PENDIENTE', 'CONFIRMADA']
    ).order_by('fecha', 'hora_inicio')
    
    citas_historial = citas.filter(
        estado__in=['ATENDIDA', 'NO_ASISTIO', 'CANCELADA']
    ).order_by('-fecha', '-hora_inicio')
    
    return render(request, 'citas/mis_citas.html', {
        'citas_proximas': citas_proximas,
        'citas_historial': citas_historial,
    })

@login_required
def confirmacion_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id, usuario=request.user)
    return render(request, 'citas/confirmacion.html', {'cita': cita})

@login_required
@require_POST
def cancelar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id, usuario=request.user)
    
    # Validar que la cita esté en estado pendiente o confirmada
    if cita.estado not in [Cita.EstadoCita.PENDIENTE, Cita.EstadoCita.CONFIRMADA]:
        messages.error(request, 'Esta cita no puede ser cancelada.')
        return redirect('citas:mis_citas')
    
    # Validar que no sea para hoy (o regla de 24 horas)
    if cita.fecha == timezone.now().date():
        hora_actual = timezone.now().time()
        hora_cita = cita.hora_inicio
        # Si la cita es hoy y ya pasó la hora de inicio, no se puede cancelar
        if hora_actual >= hora_cita:
            messages.error(request, 'No puedes cancelar una cita que ya pasó.')
            return redirect('citas:mis_citas')
    
    cita.estado = Cita.EstadoCita.CANCELADA
    cita.save()
    messages.success(request, 'Cita cancelada exitosamente.')
    return redirect('citas:mis_citas')

@staff_member_required
def dashboard(request):
    hoy = timezone.now().date()
    
    # Obtener citas del día seleccionado
    fecha_seleccionada = request.GET.get('fecha', hoy.strftime('%Y-%m-%d'))
    try:
        fecha = timezone.datetime.strptime(fecha_seleccionada, '%Y-%m-%d').date()
    except ValueError:
        fecha = hoy
    
    citas_dia = Cita.objects.filter(fecha=fecha).order_by('hora_inicio')
    
    # Obtener bloques de horario
    bloqueos = BloqueoHorario.objects.filter(fecha=fecha).order_by('hora_inicio')
    
    # Obtener fechas que tienen citas (excluyendo canceladas) con su conteo para el calendario
    citas_resumen = (
        Cita.objects.exclude(estado=Cita.EstadoCita.CANCELADA)
        .values('fecha')
        .annotate(total=Count('id'))
    )
    fechas_con_citas = {
        item['fecha'].strftime('%Y-%m-%d'): item['total']
        for item in citas_resumen
    }
    
    return render(request, 'citas/dashboard.html', {
        'citas_dia': citas_dia,
        'bloqueos': bloqueos,
        'fecha': fecha,
        'fecha_str': fecha.strftime('%Y-%m-%d'),
        'hoy': hoy,
        'fechas_con_citas_json': json.dumps(fechas_con_citas),
    })

@staff_member_required
@require_POST
def cambiar_estado_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id)
    nuevo_estado = request.POST.get('estado')
    estado_anterior = cita.estado
    
    if nuevo_estado in dict(Cita.EstadoCita.choices):
        cita.estado = nuevo_estado
        cita.save()
        
        # Si el dentista confirma la cita y antes no estaba confirmada, enviar email al paciente
        if nuevo_estado == Cita.EstadoCita.CONFIRMADA and estado_anterior != Cita.EstadoCita.CONFIRMADA:
            enviado = enviar_email_confirmacion_cita(cita, request)
            if enviado:
                messages.success(request, f'Cita confirmada y correo de confirmación enviado a {cita.usuario.email}.')
            else:
                messages.warning(request, f'Cita confirmada, pero ocurrió un problema al enviar el correo a {cita.usuario.email}.')
        else:
            messages.success(request, f'Cita actualizada a "{cita.get_estado_display()}".')
    else:
        messages.error(request, 'Estado inválido.')
    
    # Redirigir al dashboard manteniendo la fecha de la cita
    fecha_str = cita.fecha.strftime('%Y-%m-%d')
    return redirect(f"{reverse('citas:dashboard')}?fecha={fecha_str}")

@staff_member_required
def bloquear_horario(request):
    if request.method == 'POST':
        fecha_str = request.POST.get('fecha')
        motivo    = request.POST.get('motivo', '').strip()
        tipo      = request.POST.get('tipo', 'especifico')

        if not fecha_str or not motivo:
            messages.error(request, 'Todos los campos son requeridos.')
            return redirect('citas:bloquear_horario')

        try:
            fecha = timezone.datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Fecha inválida.')
            return redirect('citas:bloquear_horario')

        if tipo == 'dia_completo':
            # Usar la configuración de horarios del consultorio
            horario = DisponibilidadService._get_horario_dia(fecha)
            if not horario or not horario.activo:
                messages.error(request, 'No hay horario laboral activo configurado para ese día.')
                return redirect('citas:bloquear_horario')

            hora_inicio = horario.hora_apertura
            hora_fin    = horario.hora_cierre

            # Verificar si ya existe un bloqueo que cubra todo el día
            bloqueo_existente = BloqueoHorario.objects.filter(
                fecha=fecha, hora_inicio=hora_inicio
            ).exists()
            if bloqueo_existente:
                messages.warning(request, 'Ya existe un bloqueo para ese horario en esa fecha.')
            else:
                BloqueoHorario.objects.create(
                    fecha=fecha,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    motivo=motivo
                )
                messages.success(
                    request,
                    f'Día completo bloqueado: {fecha.strftime("%d/%m/%Y")} '
                    f'({hora_inicio.strftime("%H:%M")} - {hora_fin.strftime("%H:%M")}). '
                    f'Motivo: {motivo}'
                )

        else:  # tipo == 'especifico'
            hora_inicio_str = request.POST.get('hora_inicio')
            hora_fin_str    = request.POST.get('hora_fin')

            if not hora_inicio_str or not hora_fin_str:
                messages.error(request, 'Las horas de inicio y fin son requeridas.')
                return redirect('citas:bloquear_horario')

            try:
                hora_inicio = timezone.datetime.strptime(hora_inicio_str, '%H:%M').time()
                hora_fin    = timezone.datetime.strptime(hora_fin_str,    '%H:%M').time()
            except ValueError:
                messages.error(request, 'Formato de hora inválido.')
                return redirect('citas:bloquear_horario')

            cita_conflicto = Cita.objects.filter(
                fecha=fecha,
                hora_inicio=hora_inicio,
                estado__in=['PENDIENTE', 'CONFIRMADA']
            ).exists()

            bloqueo_existente = BloqueoHorario.objects.filter(
                fecha=fecha, hora_inicio=hora_inicio
            ).exists()

            if cita_conflicto:
                messages.error(request, 'Ya existe una cita en este horario, no se puede bloquear.')
            elif bloqueo_existente:
                messages.error(request, 'Este horario ya está bloqueado para esa fecha.')
            else:
                BloqueoHorario.objects.create(
                    fecha=fecha,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    motivo=motivo
                )
                messages.success(request, 'Horario bloqueado exitosamente.')

        return redirect('citas:bloquear_horario')

    # GET: mostrar formulario con todos los bloqueos existentes (hoy en adelante)
    bloqueos = BloqueoHorario.objects.filter(
        fecha__gte=timezone.now().date()
    ).order_by('fecha', 'hora_inicio')

    return render(request, 'citas/bloquear_horario.html', {
        'bloqueos': bloqueos,
        'hoy': timezone.now().date().strftime('%Y-%m-%d'),
    })

@staff_member_required
@require_POST
def eliminar_bloqueo(request, bloqueo_id):
    bloqueo = get_object_or_404(BloqueoHorario, id=bloqueo_id)
    bloqueo.delete()
    messages.success(request, 'Bloqueo eliminado.')
    return redirect('citas:dashboard')

@staff_member_required
@require_POST
def eliminar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id)
    fecha_str = cita.fecha.strftime('%Y-%m-%d')
    cita.delete()
    messages.success(request, 'Cita eliminada correctamente.')
    return redirect(f"{reverse('citas:dashboard')}?fecha={fecha_str}")
