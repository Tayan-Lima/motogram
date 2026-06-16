"""Serviços da app corridas — lógica de negócio."""

import os
import requests
from django.conf import settings


def notificar_motorista_telegram(telegram_id: int, mensagem: str, reply_markup: dict = None):
    """Envia mensagem ao motorista via Telegram API."""
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        return None

    payload = {
        "chat_id": telegram_id,
        "text": mensagem,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload,
            timeout=5,
        )
        return resp.json()
    except requests.RequestException:
        return None


def notificar_motoristas_proximos(corrida):
    """Notifica motoristas próximos sobre nova corrida (requer PostGIS)."""
    try:
        from django.contrib.gis.geos import Point
        from django.contrib.gis.db.models.functions import Distance
        from django.contrib.gis.measure import D
    except Exception:
        return

    from motoristas.models import Motorista

    ponto = Point(corrida.origem_lon, corrida.origem_lat, srid=4326)

    motoristas = Motorista.objects.filter(
        activo=True,
        status_cadastro="aprovado",
        telegram_id__isnull=False,
        localizacao__isnull=False,
    ).annotate(
        distancia=Distance("localizacao", ponto)
    ).filter(
        distancia__lte=D(km=5)
    ).order_by("distancia")[:5]

    for motorista in motoristas:
        distancia_km = round(motorista.distancia.km, 1) if motorista.distancia else "?"
        mensagem = (
            f"🏍️ *Nova corrida disponível!*\n\n"
            f"📍 Distância: {distancia_km} km\n"
            f"💰 Valor: R$ {corrida.valor or 'a negociar'}\n"
            f"🕐 Agora mesmo\n\n"
            f"Responde rápido!"
        )
        reply_markup = {
            "inline_keyboard": [[
                {"text": "✅ Aceitar", "callback_data": f"aceitar:{corrida.id}"},
                {"text": "❌ Recusar", "callback_data": f"recusar:{corrida.id}"},
            ]]
        }
        notificar_motorista_telegram(motorista.telegram_id, mensagem, reply_markup)
