"""Comando para cancelar corridas aguardando há mais de 10 minutos."""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from corridas.models import Corrida


class Command(BaseCommand):
    help = "Marca como sem_motoristas corridas aguardando há mais de 10 minutos"

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(minutes=10)
        corridas = Corrida.objects.filter(
            status="aguardando",
            criada_em__lt=limite,
        )
        count = corridas.count()
        corridas.update(status="sem_motoristas")
        self.stdout.write(
            self.style.SUCCESS(f"{count} corrida(s) marcada(s) como sem motoristas.")
        )
