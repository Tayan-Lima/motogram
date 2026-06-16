"""Comando para notificar motoristas com assinatura a vencer em 3 dias."""

from django.core.management.base import BaseCommand
from datetime import date, timedelta
from django.conf import settings

from motoristas.models import Motorista
import requests
import os


class Command(BaseCommand):
    help = "Notifica motoristas com assinatura a vencer em 3 dias"

    def handle(self, *args, **options):
        data_limite = date.today() + timedelta(days=3)
        motoristas = Motorista.objects.filter(
            activo=True,
            assinatura_ate=data_limite,
            telegram_id__isnull=False,
        )

        token = os.environ.get("TELEGRAM_TOKEN")
        if not token:
            self.stdout.write(self.style.ERROR("TELEGRAM_TOKEN não configurado."))
            return

        count = 0
        for motorista in motoristas:
            mensagem = (
                f"⚠️ *Assinatura a vencer!*\n\n"
                f"Olá {motorista.nome_completo},\n\n"
                f"A tua assinatura vence em {motorista.assinatura_ate.strftime('%d/%m/%Y')}.\n"
                f"Renova para continuares a receber corridas.\n\n"
                f"🔗 {settings.SITE_URL}/motorista/conta/"
            )
            try:
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id": motorista.telegram_id,
                        "text": mensagem,
                        "parse_mode": "Markdown",
                    },
                    timeout=5,
                )
                count += 1
            except requests.RequestException:
                pass

        self.stdout.write(
            self.style.SUCCESS(f"{count} motorista(s) notificado(s).")
        )
