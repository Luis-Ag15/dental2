from django.urls import path
from . import views

app_name = 'citas'

urlpatterns = [
    path('agendar/', views.agendar_cita, name='agendar'),
    path('mis-citas/', views.mis_citas, name='mis_citas'),
    path('confirmacion/<int:cita_id>/', views.confirmacion_cita, name='confirmacion'),
    path('cancelar/<int:cita_id>/', views.cancelar_cita, name='cancelar_cita'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('cambiar-estado/<int:cita_id>/', views.cambiar_estado_cita, name='cambiar_estado'),
    path('bloquear-horario/', views.bloquear_horario, name='bloquear_horario'),
    path('eliminar-bloqueo/<int:bloqueo_id>/', views.eliminar_bloqueo, name='eliminar_bloqueo'),
    path('eliminar/<int:cita_id>/', views.eliminar_cita, name='eliminar_cita'),
]
