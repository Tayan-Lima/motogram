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
    """Notifica motoristas próximos com círculo expansível e fallback em cascata.

    Estratégia:
      1. Círculo expansível (5 → 10 → 25 km) com localização fresca (≤2h)
      2. Fallback: motoristas com localização antiga (>2h)
      3. Fallback: motoristas online sem PointField (sem localização GPS)
      4. Último recurso: marcar corrida como 'sem_motoristas'
    """
    try:
        from django.contrib.gis.geos import Point
        from django.contrib.gis.db.models.functions import Distance
        from django.contrib.gis.measure import D
    except Exception as e:
        logger.exception("PostGIS indisponivel — notificacao cancelada para corrida %s", corrida.id)
        return

    from datetime import timedelta
    from django.utils import timezone
    from motoristas.models import Motorista

    try:
        ponto = Point(corrida.origem_lon, corrida.origem_lat, srid=4326)
    except Exception:
        logger.exception("Erro ao criar Point para corrida %s", corrida.id)
        return

    RAIOS_KM = [5, 10, 25]
    IDADE_MAXIMA = timedelta(hours=2)
    corte_frescura = timezone.now() - IDADE_MAXIMA

    def _redis_geosearch(corrida, raio_metros):
        """Pre-filtra motoristas por raio no Redis Geo (best-effort).
        Retorna lista de motorista IDs ou None se Redis indisponivel."""
        redis_url = os.environ.get("REDIS_URL", "")
        if not redis_url:
            return None
        try:
            import redis
            r = redis.from_url(redis_url)
            resultados = r.geosearch(
                "motoristas:loc",
                longitude=corrida.origem_lon,
                latitude=corrida.origem_lat,
                radius=raio_metros,
                unit="m",
                sort="ASC",
                count=10,
            )
            return [int(m[0]) for m in resultados]
        except Exception:
            logger.debug("_redis_geosearch: Redis indisponivel")
            return None

    def _query_motoristas(raio_km, filtro_frescura=True, limite=5, ids_filtro=None):
        qs = Motorista.objects.filter(
            activo=True,
            status_cadastro="aprovado",
            telegram_id__isnull=False,
            localizacao__isnull=False,
        )
        if ids_filtro is not None:
            qs = qs.filter(id__in=ids_filtro)
        if filtro_frescura:
            qs = qs.filter(ultima_localizacao_em__gte=corte_frescura)
        qs = qs.annotate(
            distancia=Distance("localizacao", ponto)
        ).filter(
            distancia__lte=D(km=raio_km)
        ).order_by("distancia")[:limite]
        return qs

    # ── Nível 1: Círculo expansível com localização fresca ──────
    motoristas = Motorista.objects.none()
    raio_usado = None
    ids_redis = _redis_geosearch(corrida, RAIOS_KM[-1] * 1000)
    for raio in RAIOS_KM:
        motoristas = _query_motoristas(raio, filtro_frescura=True, ids_filtro=ids_redis)
        if motoristas:
            raio_usado = raio
            break

    if motoristas:
        _enviar_notificacoes(corrida, motoristas, fresca=True, raio_usado=raio_usado)
        return

    # ── Nível 2: Motoristas com localização antiga (>2h) ─────
    logger.info(
        "notificar_motoristas_proximos: 0 motoristas frescos ate %skm para corrida %s — tentando localizacao antiga",
        RAIOS_KM[-1], corrida.id,
    )
    for raio in RAIOS_KM:
        motoristas = _query_motoristas(raio, filtro_frescura=False, limite=10, ids_filtro=ids_redis)
        if motoristas:
            raio_usado = raio
            break

    if motoristas:
        _enviar_notificacoes(corrida, motoristas, fresca=False, raio_usado=raio_usado)
        return

    # ── Nível 3: Motoristas online sem PointField ─────────────────
    logger.info(
        "notificar_motoristas_proximos: 0 motoristas com PointField para corrida %s — tentando motoristas sem GPS",
        corrida.id,
    )
    motoristas_sem_gps = Motorista.objects.filter(
        activo=True,
        status_cadastro="aprovado",
        telegram_id__isnull=False,
        localizacao__isnull=True,
    )[:10]

    if motoristas_sem_gps:
        _enviar_notificacoes_sem_gps(corrida, motoristas_sem_gps)
        return

    # ── Nível 4: Zero absoluto ────────────────────────────────────
    logger.warning(
        "notificar_motoristas_proximos: 0 motoristas disponiveis para corrida %s (origem=%s)",
        corrida.id, corrida.endereco_origem,
    )
    corrida.status = "sem_motoristas"
    corrida.save(update_fields=["status"])

    if corrida.passageiro.telegram_id:
        import threading
        threading.Thread(
            target=notificar_passageiro_telegram,
            args=(
                corrida.passageiro.telegram_id,
                "😔 Nenhum motorista disponível agora.\nTente novamente em alguns minutos.",
            ),
            daemon=True,
        ).start()


def _enviar_notificacoes(corrida, motoristas, fresca=True, raio_usado=None):
    """Envia notificações Telegram para a lista de motoristas encontrados."""
    import html

    valor = float(corrida.valor_sugerido) if corrida.valor_sugerido else 0
    origem = html.escape(corrida.endereco_origem)
    destino = html.escape(corrida.endereco_destino)
    ponto_ref = ""
    if corrida.ponto_referencia:
        ponto_ref = f"📍 Ref: {html.escape(corrida.ponto_referencia)}\n"

    alerta_stale = ""
    if not fresca:
        alerta_stale = "⚠️ Localização pode estar desatualizada\n"

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

            distancia_aviso = ""
            if raio_usado and raio_usado > 5:
                distancia_aviso = f"🔔 Expansão de raio ({raio_usado} km)\n"

            mensagem = (
                "<b>Nova solicitacao!</b>\n\n"
                f"Passageiro oferece: R$ {valor:.2f}\n"
                f"De: {origem}\n"
                f"Para: {destino}\n"
                f"Distancia: ~{distancia_km} km\n"
                f"{ponto_ref}"
                f"{alerta_stale}"
                f"{distancia_aviso}"
                f"{rating_info}"
                "Responda em ate 60 segundos!"
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
                    "Notificacao enviada para motorista %s (tg=%s) — corrida %s (raio=%s km, fresca=%s)",
                    motorista.nome_completo, motorista.telegram_id, corrida.id, raio_usado, fresca,
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


def _enviar_notificacoes_sem_gps(corrida, motoristas):
    """Notifica motoristas que estão online mas não têm PointField (localização GPS)."""
    import html

    valor = float(corrida.valor_sugerido) if corrida.valor_sugerido else 0
    origem = html.escape(corrida.endereco_origem)
    destino = html.escape(corrida.endereco_destino)
    cidade = corrida.origem_texto or "sua regiao"

    for motorista in motoristas:
        try:
            tg_str = str(motorista.telegram_id)
            mensagem = (
                "<b>Nova solicitacao na sua cidade!</b>\n\n"
                f"Passageiro oferece: R$ {valor:.2f}\n"
                f"De: {origem}\n"
                f"Para: {destino}\n"
                f"📍 Regiao: {cidade}\n\n"
                "<i>Sua localizacao nao esta definida.</i>\n"
                "📍 Compartilhe localizacao em tempo real pelo Telegram para aparecer nas buscas."
            )

            resultado = notificar_motorista_telegram(motorista.telegram_id, mensagem)
            mid = _extrair_message_id(resultado)
            if mid:
                corrida.notificacao_msg_ids[tg_str] = [mid]
                corrida.save(update_fields=["notificacao_msg_ids"])

            if resultado and resultado.get("ok"):
                logger.info(
                    "Notificacao sem-GPS enviada para motorista %s (tg=%s) — corrida %s",
                    motorista.nome_completo, motorista.telegram_id, corrida.id,
                )
        except Exception:
            logger.exception(
                "Erro ao notificar motorista sem GPS %s — corrida %s",
                motorista.nome_completo, corrida.id,
            )


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
