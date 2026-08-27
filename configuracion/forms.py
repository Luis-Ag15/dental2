from django import forms
from django.forms import inlineformset_factory
from .models import ConfiguracionConsultorio, HorarioDia


class ConfiguracionForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionConsultorio
        fields = ['nombre_consultorio', 'nombre_dentista', 'telefono', 'direccion', 'zona_horaria']
        widgets = {
            'nombre_consultorio': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_dentista':    forms.TextInput(attrs={'class': 'form-control'}),
            'telefono':           forms.TextInput(attrs={'class': 'form-control'}),
            'direccion':          forms.TextInput(attrs={'class': 'form-control'}),
            'zona_horaria':       forms.Select(attrs={'class': 'form-select'}),
        }


class HorarioDiaForm(forms.ModelForm):
    hora_apertura = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control form-control-sm'}),
        required=False,
    )
    hora_cierre = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control form-control-sm'}),
        required=False,
    )

    class Meta:
        model = HorarioDia
        fields = ['activo', 'hora_apertura', 'hora_cierre']
        widgets = {
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input day-active-toggle'}),
        }

    def clean(self):
        cleaned = super().clean()
        activo    = cleaned.get('activo')
        apertura  = cleaned.get('hora_apertura')
        cierre    = cleaned.get('hora_cierre')

        if activo:
            if not apertura:
                self.add_error('hora_apertura', 'Requerida cuando el día está activo.')
            if not cierre:
                self.add_error('hora_cierre', 'Requerida cuando el día está activo.')
            if apertura and cierre and cierre <= apertura:
                self.add_error('hora_cierre', 'La hora de cierre debe ser posterior a la apertura.')
        return cleaned


# Formset inline: 7 filas (una por día), sin agregar ni eliminar desde el form
HorarioDiaFormSet = inlineformset_factory(
    ConfiguracionConsultorio,
    HorarioDia,
    form=HorarioDiaForm,
    fields=['activo', 'hora_apertura', 'hora_cierre'],
    extra=0,
    can_delete=False,
)
