"""Serviços da app motoristas — lógica de negócio."""

import logging
import os
import secrets
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


def gerar_token_telegram(motorista):
    """Gera token único de activação Telegram (24h, uso único)."""
    token = secrets.token_urlsafe(16)
    motorista.telegram_token = token
    motorista.telegram_token_expiry = timezone.now() + timedelta(hours=24)
    motorista.save()
    return token


def validar_token_telegram(token: str):
    """Valida token de activação Telegram. Retorna Motorista ou None."""
    from .models import Motorista

    try:
        motorista = Motorista.objects.get(
            telegram_token=token,
            telegram_token_expiry__gt=timezone.now(),
        )
        motorista.telegram_token = None
        motorista.telegram_token_expiry = None
        motorista.save()
        return motorista
    except Motorista.DoesNotExist:
        return None


def activar_motorista_apos_pagamento(assinatura):
    """Activa motorista após pagamento confirmado."""
    from datetime import date, timedelta

    motorista = assinatura.motorista
    motorista.activo = True
    motorista.assinatura_ate = date.today() + timedelta(days=30)
    motorista.save()

    assinatura.status = "paga"
    assinatura.paga_em = timezone.now()
    assinatura.valida_ate = motorista.assinatura_ate
    assinatura.save()

    return motorista


def salvar_localizacao(motorista, lat, lon):
    """Actualiza localização e timestamp do motorista.
    Retorna (ok, aviso) — aviso só é preenchido se PostGIS falhou."""
    try:
        from django.contrib.gis.geos import Point
        motorista.localizacao = Point(float(lon), float(lat), srid=4326)
        motorista.ultima_localizacao_em = timezone.now()
        motorista.save(update_fields=["localizacao", "ultima_localizacao_em"])
        _redis_geoadd(motorista.id, lon, lat)
        return True, None
    except Exception:
        logger.warning("salvar_localizacao: PostGIS indisponivel para motorista %s", motorista.id)
        motorista.ultima_localizacao_em = timezone.now()
        motorista.save(update_fields=["ultima_localizacao_em"])
        _redis_geoadd(motorista.id, lon, lat)
        return True, "PostGIS indisponivel — apenas timestamp actualizado"


def _redis_geoadd(motorista_id, lon, lat):
    """Escreve localizacao no Redis Geo (best-effort).
    Se REDIS_URL nao definida ou Redis offline, falha silenciosamente."""
    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        return
    try:
        import redis
        r = redis.from_url(redis_url)
        r.geoadd("motoristas:loc", (float(lon), float(lat), str(motorista_id)))
    except Exception:
        logger.debug("_redis_geoadd: Redis indisponivel para motorista %s", motorista_id)
