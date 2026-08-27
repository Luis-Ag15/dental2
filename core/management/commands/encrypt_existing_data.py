"""
Comando para cifrar datos existentes en la BD tras aplicar los campos cifrados.
Uso: python manage.py encrypt_existing_data
"""
from django.core.management.base import BaseCommand
from core.encryption import encrypt
from usuarios.models import User
from citas.models import Cita, BloqueoHorario


class Command(BaseCommand):
    help = 'Cifra los datos existentes en la BD usando Fernet.'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando cifrado de datos existentes en Dental...\n')

        # ── User (nombre y telefono) ──────────────────────────────────────────
        total_u = 0
        for u in User.objects.all():
            update = {}
            raw_nombre = u.nombre
            raw_tel = u.telefono
            if raw_nombre and not str(raw_nombre).startswith('gAAAAA'):
                update['nombre'] = encrypt(raw_nombre)
            if raw_tel and not str(raw_tel).startswith('gAAAAA'):
                update['telefono'] = encrypt(raw_tel)
            if update:
                User.objects.filter(pk=u.pk).update(**update)
                total_u += 1
        self.stdout.write(f'  [OK] User (nombre/telefono): {total_u} registros actualizados/cifrados')

        # ── Cita.motivo ───────────────────────────────────────────────────────
        total_c = 0
        for c in Cita.objects.all():
            raw_motivo = c.motivo
            if raw_motivo and not str(raw_motivo).startswith('gAAAAA'):
                Cita.objects.filter(pk=c.pk).update(motivo=encrypt(raw_motivo))
                total_c += 1
        self.stdout.write(f'  [OK] Cita (motivo): {total_c} registros cifrados')

        # ── BloqueoHorario.motivo ─────────────────────────────────────────────
        total_b = 0
        for b in BloqueoHorario.objects.all():
            raw_motivo = b.motivo
            if raw_motivo and not str(raw_motivo).startswith('gAAAAA'):
                BloqueoHorario.objects.filter(pk=b.pk).update(motivo=encrypt(raw_motivo))
                total_b += 1
        self.stdout.write(f'  [OK] BloqueoHorario (motivo): {total_b} registros cifrados')

        self.stdout.write(self.style.SUCCESS('\nCifrado de datos existentes completado exitosamente!'))
