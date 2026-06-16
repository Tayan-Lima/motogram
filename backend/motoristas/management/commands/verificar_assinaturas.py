"""Comando para bloquear motoristas com assinatura vencida."""

from django.core.management.base import BaseCommand
from datetime import date

from motoristas.models import Motorista


class Command(BaseCommand):
    help = "Bloqueia motoristas com assinatura vencida"

    def handle(self, *args, **options):
        motoristas = Motorista.objects.filter(
            activo=True,
            assinatura_ate__lt=date.today(),
        )
        count = motoristas.count()
        motoristas.update(activo=False)
        self.stdout.write(
            self.style.SUCCESS(f"{count} motorista(s) bloqueado(s).")
        )
