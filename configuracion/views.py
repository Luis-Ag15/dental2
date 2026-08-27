from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import ConfiguracionConsultorio
from .forms import ConfiguracionForm, HorarioDiaFormSet


@staff_member_required
def configuracion(request):
    config = ConfiguracionConsultorio.get_config()

    # Garantizar que existan las 7 filas de HorarioDia
    if config.horarios.count() < 7:
        config._crear_horarios_default()

    if request.method == 'POST':
        form    = ConfiguracionForm(request.POST, instance=config)
        formset = HorarioDiaFormSet(request.POST, instance=config)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, '✅ Configuración guardada exitosamente.')
            return redirect('configuracion:configuracion')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form    = ConfiguracionForm(instance=config)
        formset = HorarioDiaFormSet(instance=config)

    # Adjuntar nombre del día a cada subform para usarlo en el template
    dias_nombres = {
        '1': ('Lunes',     'fas fa-sun'),
        '2': ('Martes',    'fas fa-sun'),
        '3': ('Miércoles', 'fas fa-sun'),
        '4': ('Jueves',    'fas fa-sun'),
        '5': ('Viernes',   'fas fa-sun'),
        '6': ('Sábado',    'fas fa-umbrella-beach'),
        '7': ('Domingo',   'fas fa-church'),
    }
    horario_forms = []
    for subform in formset:
        dia_val = str(subform.instance.dia)
        nombre, icono = dias_nombres.get(dia_val, ('Día', 'fas fa-calendar'))
        horario_forms.append({'form': subform, 'nombre': nombre, 'icono': icono})

    return render(request, 'configuracion/configuracion.html', {
        'form':          form,
        'formset':       formset,
        'horario_forms': horario_forms,
        'config':        config,
    })
