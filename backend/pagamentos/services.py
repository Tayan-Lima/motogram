"""Serviços da app pagamentos — lógica de criação de Pix e webhook."""

import hmac
import hashlib
import requests
from django.conf import settings


def criar_pix_mercadopago(motorista, valor, pix_txid):
    """Cria cobrança Pix via API Mercado Pago.

    Args:
        motorista: instância do Motorista
        valor: valor em centavos (ex: 6900 = R$ 69,00)
        pix_txid: identificador único da transação

    Returns:
        dict com chaves 'pix_copia_cola' e 'qr_code_base64'
    """
    access_token = settings.MP_ACCESS_TOKEN
    if not access_token:
        return {}

    try:
        resp = requests.post(
            "https://api.mercadopago.com/v1/payments",
            json={
                "transaction_amount": valor / 100.0,
                "description": f"Assinatura MotoGram — {motorista.nome_completo}",
                "payment_method_id": "pix",
                "payer": {
                    "email": motorista.utilizador.email,
                    "first_name": motorista.nome_completo.split()[0],
                },
                "external_reference": pix_txid,
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        data = resp.json()
        return {
            "pix_copia_cola": data.get("point_of_interaction", {}).get(
                "transaction_data", {}
            ).get("qr_code", ""),
            "qr_code_base64": data.get("point_of_interaction", {}).get(
                "transaction_data", {}
            ).get("qr_code_base64", ""),
        }
    except requests.RequestException:
        return {}


def verificar_assinatura_webhook(request):
    secret = settings.MP_WEBHOOK_SECRET
    if not secret:
        return True

    signature = request.headers.get("X-Signature", "")
    x_request_id = request.headers.get("X-Request-Id", "")

    expected = hmac.new(
        secret.encode(),
        f"{x_request_id}{request.body.decode()}".encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


def processar_webhook_mercadopago(data):
    from .models import Assinatura
    from motoristas.services import activar_motorista_apos_pagamento

    payment_id = data.get("data", {}).get("id")
    payment_type = data.get("type")

    if payment_type != "payment" or not payment_id:
        return

    try:
        assinatura = Assinatura.objects.get(pix_txid=payment_id, status="pendente")
    except Assinatura.DoesNotExist:
        return

    activar_motorista_apos_pagamento(assinatura)
