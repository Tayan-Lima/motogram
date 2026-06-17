"""Serviços HTTP para comunicação com o backend Django."""

import os
import requests

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
        return resp.json()
    except requests.RequestException:
        return {"active": False, "message": "Erro de conexão com o servidor."}


def activar_telegram(token: str, telegram_id: int) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/motoristas/activar-telegram/",
            json={"token": token, "telegram_id": telegram_id},
            headers=_headers(),
            timeout=5,
        )
        return resp.json()
    except requests.RequestException:
        return {"erro": "Erro de conexão com o servidor."}


def aceitar_corrida(corrida_id: int, motorista_telegram_id: int) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/corridas/{corrida_id}/aceitar/",
            json={"motorista_telegram_id": motorista_telegram_id},
            headers=_headers(),
            timeout=5,
        )
        return resp.json()
    except requests.RequestException:
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
        return resp.json()
    except requests.RequestException:
        return {"erro": "Erro de conexão com o servidor."}


def recusar_corrida(corrida_id: int, motorista_telegram_id: int) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/corridas/{corrida_id}/recusar/",
            json={"motorista_telegram_id": motorista_telegram_id},
            headers=_headers(),
            timeout=5,
        )
        return resp.json()
    except requests.RequestException:
        return {"erro": "Erro de conexão com o servidor."}


def concluir_corrida(corrida_id: int, motorista_telegram_id: int) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/corridas/{corrida_id}/concluir/",
            json={"motorista_telegram_id": motorista_telegram_id},
            headers=_headers(),
            timeout=5,
        )
        return resp.json()
    except requests.RequestException:
        return {"erro": "Erro de conexão com o servidor."}
