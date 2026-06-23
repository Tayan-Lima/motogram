"""Serviços de geocoding — HERE Maps API (primary) + Nominatim (fallback).

A chave HERE nunca é exposta no frontend. Todas as chamadas HERE passam
por este módulo no backend Django. Se HERE falhar (5xx, timeout), cai
para Nominatim com User-Agent próprio. Resultados são cacheados em
LocMemCache (TTL 24h) para poupar quota HERE (250k transações/mês).
"""

import hashlib
import logging
from django.conf import settings
from django.core.cache import cache

import requests

logger = logging.getLogger(__name__)

HERE_GEOCODE_URL = "https://geocode.search.hereapi.com/v1/geocode"
HERE_AUTOCOMPLETE_URL = "https://autocomplete.search.hereapi.com/v1/autocomplete"
HERE_REVERSE_URL = "https://revgeocode.search.hereapi.com/v1/revgeocode"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {
    "Accept-Language": "pt-BR",
    "User-Agent": "Motogram/1.0",
}

_CACHE_TTL = 86400  # 24h
_CACHE_PREFIX = "here_geo:"


def _here_api_key():
    return getattr(settings, "HERE_API_KEY", "")


def _cache_key(prefix, *parts):
    raw = ":".join(str(p) for p in parts)
    h = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"{_CACHE_PREFIX}{prefix}:{h}"


def _cache_get(key):
    return cache.get(key)


def _cache_set(key, value):
    cache.set(key, value, _CACHE_TTL)


def autocomplete(query, lat=None, lng=None, limit=5):
    """Sugestões de endereço enquanto o utilizador digita.

    Usa HERE Autocomplete API. Se HERE falhar, tenta Nominatim.
    Retorna lista de dicts: [{label, lat, lng, id}, ...]
    """
    if not query or len(query) < 3:
        return []

    cache_key = _cache_key("auto", query.lower(), lat or 0, lng or 0, limit)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    results = _here_autocomplete(query, lat, lng, limit)
    if results is None:
        results = _nominatim_search(query, limit)
        if results is None:
            results = []

    _cache_set(cache_key, results)
    return results


def geocode(address, lat=None, lng=None):
    """Converte endereço completo em coordenadas.

    Usa HERE Geocode API. Se HERE falhar, tenta Nominatim.
    Retorna dict {lat, lng, label} ou None.
    """
    if not address or len(address) < 3:
        return None

    cache_key = _cache_key("geo", address.lower(), lat or 0, lng or 0)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    result = _here_geocode(address, lat, lng)
    if result is None:
        result = _nominatim_geocode(address)
        if result is None:
            return None

    _cache_set(cache_key, result)
    return result


def reverse_geocode(lat, lng):
    """Converte coordenadas em endereço legível.

    Usa HERE Reverse Geocode API. Se HERE falhar, retorna None
    (Nominatim reverse é lento e pouco fiável para fallback).
    Retorna string (label) ou None.
    """
    if lat is None or lng is None:
        return None

    cache_key = _cache_key("rev", f"{lat:.5f}", f"{lng:.5f}")
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    result = _here_reverse(lat, lng)
    if result is not None:
        _cache_set(cache_key, result)
    return result


def _here_autocomplete(query, lat, lng, limit):
    api_key = _here_api_key()
    if not api_key:
        logger.warning("autocomplete: HERE_API_KEY não configurada, tentando Nominatim")
        return None

    params = {
        "q": query,
        "apiKey": api_key,
        "lang": "pt-BR",
        "limit": limit,
        "in": "countryCode:BRA",
    }
    if lat is not None and lng is not None:
        params["at"] = f"{lat},{lng}"

    try:
        resp = requests.get(HERE_AUTOCOMPLETE_URL, params=params, timeout=5)
        if resp.status_code == 429:
            logger.warning("autocomplete: HERE rate limited (429), tentando Nominatim")
            return None
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        return [
            {
                "label": item.get("address", {}).get("label", item.get("title", "")),
                "lat": item.get("position", {}).get("lat"),
                "lng": item.get("position", {}).get("lng"),
                "id": item.get("id", ""),
            }
            for item in items
            if item.get("position")
        ]
    except requests.RequestException as e:
        logger.warning("autocomplete: HERE falhou (%s), tentando Nominatim", e)
        return None


def _here_geocode(address, lat, lng):
    api_key = _here_api_key()
    if not api_key:
        logger.warning("geocode: HERE_API_KEY não configurada, tentando Nominatim")
        return None

    params = {
        "q": address,
        "apiKey": api_key,
        "lang": "pt-BR",
        "limit": 1,
        "in": "countryCode:BRA",
    }
    if lat is not None and lng is not None:
        params["at"] = f"{lat},{lng}"

    try:
        resp = requests.get(HERE_GEOCODE_URL, params=params, timeout=8)
        if resp.status_code == 429:
            logger.warning("geocode: HERE rate limited (429), tentando Nominatim")
            return None
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            return None
        item = items[0]
        pos = item.get("position", {})
        if not pos:
            return None
        return {
            "lat": pos.get("lat"),
            "lng": pos.get("lng"),
            "label": item.get("address", {}).get("label", item.get("title", address)),
        }
    except requests.RequestException as e:
        logger.warning("geocode: HERE falhou (%s), tentando Nominatim", e)
        return None


def _here_reverse(lat, lng):
    api_key = _here_api_key()
    if not api_key:
        logger.warning("reverse_geocode: HERE_API_KEY não configurada")
        return None

    params = {
        "at": f"{lat},{lng}",
        "apiKey": api_key,
        "lang": "pt-BR",
        "limit": 1,
    }
    try:
        resp = requests.get(HERE_REVERSE_URL, params=params, timeout=5)
        if resp.status_code == 429:
            logger.warning("reverse_geocode: HERE rate limited (429)")
            return None
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            return None
        return items[0].get("address", {}).get("label") or items[0].get("title")
    except requests.RequestException as e:
        logger.warning("reverse_geocode: HERE falhou (%s)", e)
        return None


def _nominatim_search(query, limit):
    """Fallback: Nominatim search (autocomplete-like)."""
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={
                "format": "json",
                "q": query + ", Brasil",
                "limit": limit,
                "countrycodes": "br",
            },
            headers=NOMINATIM_HEADERS,
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return [
            {
                "label": item.get("display_name", ""),
                "lat": float(item["lat"]) if item.get("lat") else None,
                "lng": float(item["lon"]) if item.get("lon") else None,
                "id": "",
            }
            for item in data
            if item.get("lat") and item.get("lon")
        ]
    except (requests.RequestException, ValueError) as e:
        logger.warning("nominatim_search falhou: %s", e)
        return None


def _nominatim_geocode(address):
    """Fallback: Nominatim geocode (endereço completo → coords)."""
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={
                "format": "json",
                "q": address + ", Brasil",
                "limit": 1,
                "countrycodes": "br",
            },
            headers=NOMINATIM_HEADERS,
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data or not isinstance(data, list):
            return None
        item = data[0]
        if not item.get("lat") or not item.get("lon"):
            return None
        return {
            "lat": float(item["lat"]),
            "lng": float(item["lon"]),
            "label": item.get("display_name", address),
        }
    except (requests.RequestException, ValueError) as e:
        logger.warning("nominatim_geocode falhou: %s", e)
        return None
