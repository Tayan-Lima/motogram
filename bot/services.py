"""Serviços HTTP para comunicação com o backend Django."""

import os
import logging
import requests

logger = logging.getLogger(__name__)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
BOT_SECRET = os.environ.get("BOT_SECRET", "")


def _headers():
    return {"X-Bot-Secret": BOT_SECRET, "Content-Type": "application/json"}


def verificar_assinatura(telegram_id: int) -> dict:
    try:
        resp = requests.get(
            f"{BACKEND_URL}/api/motoristas/verificar-assinatura/",
            params={"telegram_id": telegram_id},
            headers=_headers(),
            timeout=5,
        )
        data = resp.json()
        if not resp.ok:
            logger.warning("verificar_assinatura falhou: %s %s", resp.status_code, data)
        return data
    except requests.RequestException as e:
        logger.error("verificar_assinatura erro: %s", e)
        return {"active": False, "message": "Erro de conexão com o servidor."}


def activar_telegram(token: str, telegram_id: int) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/motoristas/activar-telegram/",
            json={"token": token, "telegram_id": telegram_id},
            headers=_headers(),
            timeout=5,
        )
        data = resp.json()
        if not resp.ok:
            logger.warning("activar_telegram falhou: %s %s", resp.status_code, data)
        return data
    except requests.RequestException as e:
        logger.error("activar_telegram erro: %s", e)
        return {"erro": "Erro de conexão com o servidor."}


def aceitar_corrida(corrida_id: int, motorista_telegram_id: int) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/corridas/{corrida_id}/aceitar/",
            json={"motorista_telegram_id": motorista_telegram_id},
            headers=_headers(),
            timeout=5,
        )
        data = resp.json()
        if not resp.ok:
            logger.warning("aceitar_corrida falhou: %s %s", resp.status_code, data)
        return data
    except requests.RequestException as e:
        logger.error("aceitar_corrida erro: %s", e)
        return {"erro": "Erro de conexão com o servidor."}


def ofertar_corrida(corrida_id: int, motorista_telegram_id: int, valor: float) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/corridas/{corrida_id}/ofertar/",
            json={
                "motorista_telegram_id": motorista_telegram_id,
                "valor": valor,
            },
            headers=_headers(),
            timeout=5,
        )
        data = resp.json()
        if not resp.ok:
            logger.warning("ofertar_corrida falhou: %s %s", resp.status_code, data)
        return data
    except requests.RequestException as e:
        logger.error("ofertar_corrida erro: %s", e)
        return {"erro": "Erro de conexão com o servidor."}


def recusar_corrida(corrida_id: int, motorista_telegram_id: int) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/corridas/{corrida_id}/recusar/",
            json={"motorista_telegram_id": motorista_telegram_id},
            headers=_headers(),
            timeout=5,
        )
        data = resp.json()
        if not resp.ok:
            logger.warning("recusar_corrida falhou: %s %s", resp.status_code, data)
        return data
    except requests.RequestException as e:
        logger.error("recusar_corrida erro: %s", e)
        return {"erro": "Erro de conexão com o servidor."}


def concluir_corrida(corrida_id: int, motorista_telegram_id: int) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/corridas/{corrida_id}/concluir/",
            json={"motorista_telegram_id": motorista_telegram_id},
            headers=_headers(),
            timeout=5,
        )
        data = resp.json()
        if not resp.ok:
            logger.warning("concluir_corrida falhou: %s %s", resp.status_code, data)
        return data
    except requests.RequestException as e:
        logger.error("concluir_corrida erro: %s", e)
        return {"erro": "Erro de conexão com o servidor."}


def iniciar_corrida(corrida_id: int, motorista_telegram_id: int) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/corridas/{corrida_id}/iniciar/",
            json={"motorista_telegram_id": motorista_telegram_id},
            headers=_headers(),
            timeout=5,
        )
        data = resp.json()
        if not resp.ok:
            logger.warning("iniciar_corrida falhou: %s %s", resp.status_code, data)
        return data
    except requests.RequestException as e:
        logger.error("iniciar_corrida erro: %s", e)
        return {"erro": "Erro de conexão com o servidor."}


def cancelar_corrida_motorista(corrida_id: int, motorista_telegram_id: int) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/corridas/{corrida_id}/cancelar-motorista/",
            json={"motorista_telegram_id": motorista_telegram_id},
            headers=_headers(),
            timeout=5,
        )
        data = resp.json()
        if not resp.ok:
            logger.warning("cancelar_corrida_motorista falhou: %s %s", resp.status_code, data)
        return data
    except requests.RequestException as e:
        logger.error("cancelar_corrida_motorista erro: %s", e)
        return {"erro": "Erro de conexão com o servidor."}


def limpar_mensagens(motorista_telegram_id: int) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/motoristas/limpar-mensagens/",
            json={"motorista_telegram_id": motorista_telegram_id},
            headers=_headers(),
            timeout=10,
        )
        data = resp.json()
        if not resp.ok:
            logger.warning("limpar_mensagens falhou: %s %s", resp.status_code, data)
        return data
    except requests.RequestException as e:
        logger.error("limpar_mensagens erro: %s", e)
        return {"erro": "Erro de conexão com o servidor."}


def avaliar_passageiro(corrida_id: int, motorista_telegram_id: int, nota: int | None, comentario: str = "") -> dict:
    try:
        body = {
            "motorista_telegram_id": motorista_telegram_id,
            "comentario": comentario,
        }
        if nota is not None:
            body["nota"] = nota
        resp = requests.post(
            f"{BACKEND_URL}/api/corridas/{corrida_id}/avaliar-passageiro/",
            json=body,
            headers=_headers(),
            timeout=5,
        )
        data = resp.json()
        if not resp.ok:
            logger.warning("avaliar_passageiro falhou: %s %s", resp.status_code, data)
        return data
    except requests.RequestException as e:
        logger.error("avaliar_passageiro erro: %s", e)
        return {"erro": "Erro de conexão com o servidor."}


def atualizar_localizacao(telegram_id: int, latitude: float, longitude: float) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/motoristas/atualizar-localizacao/",
            json={
                "telegram_id": telegram_id,
                "latitude": latitude,
                "longitude": longitude,
            },
            headers=_headers(),
            timeout=5,
        )
        data = resp.json()
        if not resp.ok:
            logger.warning("atualizar_localizacao falhou: %s %s", resp.status_code, data)
        return data
    except requests.RequestException as e:
        logger.error("atualizar_localizacao erro: %s", e)
        return {"erro": "Erro de conexão com o servidor."}


def toggle_online(telegram_id: int, activo: bool) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/motoristas/toggle-online-bot/",
            json={"telegram_id": telegram_id, "activo": activo},
            headers=_headers(),
            timeout=5,
        )
        data = resp.json()
        if not resp.ok:
            logger.warning("toggle_online falhou: %s %s", resp.status_code, data)
        return data
    except requests.RequestException as e:
        logger.error("toggle_online erro: %s", e)
        return {"erro": "Erro de conexão com o servidor."}
