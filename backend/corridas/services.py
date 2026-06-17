"""Serviços da app corridas — lógica de negócio."""

import os
import requests
from django.conf import settings


def _token():
    return os.environ.get("TELEGRAM_TOKEN")


def enviar_localizacao_telegram(telegram_id: int, lat: float, lon: float):
    token = _token()
    if not token:
        return None
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendLocation",
            json={"chat_id": telegram_id, "latitude": lat, "longitude": lon},
            timeout=5,
        )
        return resp.json()
    except requests.RequestException:
        return None


def notificar_motorista_telegram(telegram_id: int, mensagem: str, reply_markup: dict = None):
    token = _token()
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

    valor = float(corrida.valor_sugerido) if corrida.valor_sugerido else 0
    origem = f"{corrida.origem_lat:.4f}, {corrida.origem_lon:.4f}"
    destino = f"{corrida.destino_lat:.4f}, {corrida.destino_lon:.4f}" if corrida.destino_lat else "(sem destino)"
    ponto_ref = f"📍 Ref: {corrida.ponto_referencia}\n" if corrida.ponto_referencia else ""

    for motorista in motoristas:
        distancia_km = round(motorista.distancia.km, 1) if motorista.distancia else "?"

        enviar_localizacao_telegram(motorista.telegram_id, corrida.origem_lat, corrida.origem_lon)

        if corrida.destino_lat and corrida.destino_lon:
            enviar_localizacao_telegram(motorista.telegram_id, corrida.destino_lat, corrida.destino_lon)

        mensagem = (
            f"🚨 *Nova solicitação!*\n\n"
            f"💰 Passageiro oferece: R$ {valor:.2f}\n"
            f"📍 De: {origem}\n"
            f"📍 Para: {destino}\n"
            f"📏 Distância: ~{distancia_km} km\n"
            f"{ponto_ref}"
            f"⏱️ Responde em até 60 segundos!"
        )

        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": f"✅ Aceitar R$ {valor:.2f}", "callback_data": f"aceitar:{corrida.id}:{valor}"},
                ],
                [
                    {"text": "💬 Oferecer outro valor", "callback_data": f"ofertar:{corrida.id}"},
                    {"text": "❌ Recusar", "callback_data": f"recusar:{corrida.id}"},
                ],
            ]
        }

        notificar_motorista_telegram(motorista.telegram_id, mensagem, reply_markup)
