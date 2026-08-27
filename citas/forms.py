from django import forms
from django.utils import timezone
from .models import Cita

SERVICIOS_CLINICA = [
    ('', '-- Selecciona un servicio --'),
    ('Consulta general / Revisión', 'Consulta general / Revisión'),
    ('Limpieza dental (Profilaxis)', 'Limpieza dental (Profilaxis)'),
    ('Blanqueamiento dental', 'Blanqueamiento dental'),
    ('Extracción dental', 'Extracción dental'),
    ('Endodoncia (Tratamiento de conducto)', 'Endodoncia (Tratamiento de conducto)'),
    ('Ortodoncia', 'Ortodoncia'),
    ('Implantes dentales', 'Implantes dentales'),
    ('Coronas y puentes', 'Coronas y puentes'),
    ('Periodoncia (Tratamiento de encías)', 'Periodoncia (Tratamiento de encías)'),
    ('Odontopediatría', 'Odontopediatría'),
    ('Urgencia dental', 'Urgencia dental'),
    ('Radiografía dental', 'Radiografía dental'),
]

class AgendarCitaForm(forms.ModelForm):
    fecha = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    motivo = forms.ChoiceField(
        choices=SERVICIOS_CLINICA,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    hora = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Cita
        fields = ['fecha', 'motivo', 'hora']

    def __init__(self, *args, **kwargs):
        self.horarios_disponibles = kwargs.pop('horarios_disponibles', [])
        super().__init__(*args, **kwargs)
        if self.horarios_disponibles:
            self.fields['hora'].choices = [(hora, hora) for hora in self.horarios_disponibles]
        elif self.data and self.data.get('hora'):
            self.fields['hora'].choices = [(self.data.get('hora'), self.data.get('hora'))]

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if fecha < timezone.now().date():
            raise forms.ValidationError('No puedes agendar citas en fechas pasadas.')
        return fecha

    def clean_motivo(self):
        motivo = self.cleaned_data.get('motivo')
        if not motivo:
            raise forms.ValidationError('Por favor selecciona un servicio.')
        return motivo
