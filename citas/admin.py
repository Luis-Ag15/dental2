from django.contrib import admin
from .models import Cita, BloqueoHorario


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'fecha', 'hora_inicio', 'hora_fin', 'motivo', 'estado', 'created_at')
    list_filter = ('estado', 'fecha')
    search_fields = ('usuario__email',)
    ordering = ('-fecha', 'hora_inicio')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('estado',)
    date_hierarchy = 'fecha'

    fieldsets = (
        ('Paciente', {'fields': ('usuario',)}),
        ('Horario', {'fields': ('fecha', 'hora_inicio', 'hora_fin')}),
        ('Detalles', {'fields': ('motivo', 'estado')}),
        ('Registro', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(BloqueoHorario)
class BloqueoHorarioAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'hora_inicio', 'hora_fin', 'motivo', 'created_at')
    list_filter = ('fecha',)
    ordering = ('-fecha', 'hora_inicio')
    readonly_fields = ('created_at',)
    date_hierarchy = 'fecha'
