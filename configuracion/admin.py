from django.contrib import admin
from .models import ConfiguracionConsultorio


@admin.register(ConfiguracionConsultorio)
class ConfiguracionAdmin(admin.ModelAdmin):
    list_display = ('nombre_consultorio', 'nombre_dentista', 'telefono', 'zona_horaria')

    def has_add_permission(self, request):
        # Solo permitir un registro
        return not ConfiguracionConsultorio.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
