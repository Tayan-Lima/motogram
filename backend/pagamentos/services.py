"""Serviços da app pagamentos — lógica de criação de Pix."""

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
