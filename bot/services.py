"""Serviços HTTP para comunicação com o backend Django."""

import os
import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
BOT_SECRET = os.environ.get("BOT_SECRET", "")


def _headers():
    return {"X-Bot-Secret": BOT_SECRET, "Content-Type": "application/json"}


def verificar_assinatura(telegram_id: int) -> dict:
    """Verifica se o motorista tem assinatura activa."""
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


def criar_corrida(passageiro_telegram_id: int, lat: float, lon: float,
                  destino_lat: float = None, destino_lon: float = None) -> dict:
    """Cria uma nova corrida no backend."""
    try:
        payload = {
            "passageiro_telegram_id": passageiro_telegram_id,
            "origem_lat": lat,
            "origem_lon": lon,
        }
        if destino_lat and destino_lon:
            payload["destino_lat"] = destino_lat
            payload["destino_lon"] = destino_lon

        resp = requests.post(
            f"{BACKEND_URL}/api/corridas/",
            json=payload,
            headers=_headers(),
            timeout=5,
        )
        return resp.json()
    except requests.RequestException:
        return {"erro": "Erro de conexão com o servidor."}


def aceitar_corrida(corrida_id: int, motorista_telegram_id: int) -> dict:
    """Motorista aceita uma corrida."""
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


def recusar_corrida(corrida_id: int, motorista_telegram_id: int) -> dict:
    """Motorista recusa uma corrida."""
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
    """Motorista conclui uma corrida."""
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


def buscar_motoristas_proximos(lat: float, lon: float, raio_km: float = 5) -> list:
    """Busca motoristas activos num raio (chamado pelo backend, não pelo bot)."""
    try:
        resp = requests.get(
            f"{BACKEND_URL}/api/motoristas/proximos/",
            params={"lat": lat, "lon": lon, "raio": raio_km},
            headers=_headers(),
            timeout=5,
        )
        return resp.json()
    except requests.RequestException:
        return []
