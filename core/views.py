from django.shortcuts import render
from configuracion.models import ConfiguracionConsultorio

def index(request):
    try:
        config = ConfiguracionConsultorio.get_config()
        horarios = config.horarios.all().order_by('dia')
    except Exception:
        config = None
        horarios = []
    return render(request, 'core/index.html', {
        'config': config,
        'horarios': horarios,
    })


def servicios(request):
    return render(request, 'core/servicios.html')

def contacto(request):
    try:
        config = ConfiguracionConsultorio.get_config()
        horarios = config.horarios.all().order_by('dia')
    except Exception:
        config = None
        horarios = []
    return render(request, 'core/contacto.html', {
        'config': config,
        'horarios': horarios,
    })

def terminos(request):
    try:
        config = ConfiguracionConsultorio.get_config()
    except Exception:
        config = None
    return render(request, 'core/terminos.html', {'config': config})

def privacidad(request):
    try:
        config = ConfiguracionConsultorio.get_config()
    except Exception:
        config = None
    return render(request, 'core/privacidad.html', {'config': config})
