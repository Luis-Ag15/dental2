"""
Campos Django personalizados con cifrado Fernet transparente.
Cifran al guardar en BD y descifran al leer — sin cambios en el resto del código.
"""
from django.db import models
from .encryption import encrypt, decrypt


class EncryptedMixin:
    """Mixin que añade cifrado/descifrado transparente a cualquier campo de texto."""

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return decrypt(value)

    def to_python(self, value):
        if value is None:
            return value
        # Si ya llegó descifrado (e.g. desde un formulario), lo devuelve directamente
        return value

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        # Evitar doble cifrado: si ya empieza con 'gAAAAA' es un token Fernet
        if isinstance(value, str) and value.startswith('gAAAAA'):
            return value
        return encrypt(str(value))


class EncryptedCharField(EncryptedMixin, models.TextField):
    """CharField cifrado. Se almacena como TextField en la BD (el cifrado agranda el valor)."""

    def __init__(self, *args, **kwargs):
        # Ignorar max_length para la BD (el campo cifrado siempre es TextField)
        kwargs.pop('max_length', None)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs


class EncryptedTextField(EncryptedMixin, models.TextField):
    """TextField cifrado."""
    pass
