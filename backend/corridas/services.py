"""Serviços da app corridas — lógica de negócio."""

import html
import logging
import os
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _token():
    return os.environ.get("TELEGRAM_TOKEN")


def _extrair_message_id(resultado):
    if resultado and resultado.get("ok"):
        return resultado.get("result", {}).get("message_id")
    return None


def _limpar_mensagens_antigas(telegram_id):
    from corridas.models import Corrida

    token = _token()
    if not token:
        return

    tg_str = str(telegram_id)
    corridas = Corrida.objects.exclude(notificacao_msg_ids={}).order_by("-id")[:20]

    for corrida in corridas[2:]:
        msg_ids = corrida.notificacao_msg_ids.pop(tg_str, None)
        if msg_ids:
            corrida.save(update_fields=["notificacao_msg_ids"])
            for msg_id in msg_ids:
                try:
                    requests.post(
                        f"https://api.telegram.org/bot{token}/deleteMessage",
                        json={"chat_id": telegram_id, "message_id": msg_id},
                        timeout=5,
                    )
                except Exception as e:
                    logger.debug("Falha ao apagar msg %s: %s", msg_id, e)


def _limpeza_agressiva(telegram_id: int, max_id_manter: int):
    """Apaga mensagens com IDs sequenciais (1 até max_id_manter-1), ignorando falhas."""
    token = _token()
    if not token:
        return

    apagadas = 0
    for mid in range(1, max_id_manter):
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/deleteMessage",
                json={"chat_id": telegram_id, "message_id": mid},
                timeout=2,
            )
            if resp.json().get("ok"):
                apagadas += 1
        except Exception as e:
            logger.debug("Falha ao apagar msg %s: %s", mid, e)

    logger.info(
        "_limpeza_agressiva: apagadas=%d de %d tentativas para tg=%s",
        apagadas, max_id_manter - 1, telegram_id,
    )


def enviar_localizacao_telegram(telegram_id: int, lat: float, lon: float):
    token = _token()
    if not token:
        logger.warning("enviar_localizacao_telegram: TELEGRAM_TOKEN nao definido")
        return None
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendLocation",
            json={"chat_id": telegram_id, "latitude": lat, "longitude": lon},
            timeout=5,
        )
        data = resp.json()
        if not data.get("ok"):
            logger.warning(
                "enviar_localizacao_telegram falhou para tg=%s: status=%s body=%s",
                telegram_id, resp.status_code, data,
            )
        return data
    except requests.RequestException as e:
        logger.warning("enviar_localizacao_telegram erro de rede para tg=%s: %s", telegram_id, e)
        return None


def notificar_motorista_telegram(telegram_id: int, mensagem: str, reply_markup: dict = None):
    token = _token()
    if not token:
        logger.warning("notificar_motorista_telegram: TELEGRAM_TOKEN nao definido")
        return None

    payload = {
        "chat_id": telegram_id,
        "text": mensagem,
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload,
            timeout=5,
        )
        data = resp.json()
        if not data.get("ok"):
            logger.warning(
                "notificar_motorista_telegram falhou para tg=%s: status=%s body=%s",
                telegram_id, resp.status_code, data,
            )
        return data
    except requests.RequestException as e:
        logger.warning("notificar_motorista_telegram erro de rede para tg=%s: %s", telegram_id, e)
        return None


def notificar_motoristas_proximos(corrida):
    try:
        from django.contrib.gis.geos import Point
        from django.contrib.gis.db.models.functions import Distance
        from django.contrib.gis.measure import D
    except Exception as e:
        logger.exception("PostGIS indisponivel — notificacao cancelada para corrida %s", corrida.id)
        return

    from motoristas.models import Motorista

    try:
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

        if not motoristas:
            logger.info(
                "notificar_motoristas_proximos: 0 motoristas no raio de 5km para corrida %s (origem=%s)",
                corrida.id, corrida.endereco_origem,
            )
            return

        valor = float(corrida.valor_sugerido) if corrida.valor_sugerido else 0
        origem = html.escape(corrida.endereco_origem)
        destino = html.escape(corrida.endereco_destino)
        ponto_ref = ""
        if corrida.ponto_referencia:
            ponto_ref = f"📍 Ref: {html.escape(corrida.ponto_referencia)}\n"

        for motorista in motoristas:
            try:
                distancia_km = round(motorista.distancia.km, 1) if motorista.distancia else "?"
                msg_ids = []
                tg_str = str(motorista.telegram_id)

                r1 = enviar_localizacao_telegram(motorista.telegram_id, corrida.origem_lat, corrida.origem_lon)
                mid = _extrair_message_id(r1)
                if mid:
                    msg_ids.append(mid)

                if corrida.destino_lat and corrida.destino_lon:
                    r2 = enviar_localizacao_telegram(motorista.telegram_id, corrida.destino_lat, corrida.destino_lon)
                    mid = _extrair_message_id(r2)
                    if mid:
                        msg_ids.append(mid)

                rating_info = ""
                passageiro_media = corrida.passageiro.media_avaliacoes
                passageiro_total = corrida.passageiro.total_corridas_concluidas
                if passageiro_media is not None:
                    estrelas = "⭐" * round(passageiro_media)
                    rating_info = f"Passageiro: {estrelas} {passageiro_media} · {passageiro_total} corridas\n"

                mensagem = (
                    "<b>Nova solicitacao!</b>\n\n"
                    f"Passageiro oferece: R$ {valor:.2f}\n"
                    f"De: {origem}\n"
                    f"Para: {destino}\n"
                    f"Distancia: ~{distancia_km} km\n"
                    f"{ponto_ref}"
                    f"{rating_info}"
                    "Responde em ate 60 segundos!"
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

                resultado = notificar_motorista_telegram(motorista.telegram_id, mensagem, reply_markup)
                mid = _extrair_message_id(resultado)
                if mid:
                    msg_ids.append(mid)

                if msg_ids:
                    corrida.notificacao_msg_ids[tg_str] = msg_ids
                    corrida.save(update_fields=["notificacao_msg_ids"])

                if resultado and resultado.get("ok"):
                    logger.info(
                        "Notificacao enviada para motorista %s (tg=%s) — corrida %s",
                        motorista.nome_completo, motorista.telegram_id, corrida.id,
                    )
                else:
                    logger.warning(
                        "Falha ao notificar motorista %s (tg=%s) — corrida %s: %s",
                        motorista.nome_completo, motorista.telegram_id, corrida.id, resultado,
                    )
            except Exception:
                logger.exception(
                    "Erro ao notificar motorista %s (tg=%s) — corrida %s",
                    motorista.nome_completo, motorista.telegram_id, corrida.id,
                )

    except Exception:
        logger.exception("Erro ao notificar motoristas para corrida %s", corrida.id)


def notificar_passageiro_telegram(telegram_id: int, mensagem: str):
    """Envia notificação ao passageiro via Telegram (se tiver telegram_id)."""
    if not telegram_id:
        return None
    token = _token()
    if not token:
        logger.warning("notificar_passageiro_telegram: TELEGRAM_TOKEN nao definido")
        return None
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": telegram_id, "text": mensagem, "parse_mode": "HTML"},
            timeout=5,
        )
        data = resp.json()
        if not data.get("ok"):
            logger.warning(
                "notificar_passageiro_telegram falhou para tg=%s: status=%s body=%s",
                telegram_id, resp.status_code, data,
            )
        return data
    except requests.RequestException as e:
        logger.warning("notificar_passageiro_telegram erro de rede para tg=%s: %s", telegram_id, e)
        return None


def calcular_distancia_km(lat1, lon1, lat2, lon2):
    """Distância em km entre dois pontos (fórmula de Haversine)."""
    import math
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 1)
