"""Serviços da app pagamentos — lógica de criação de Pix e webhook."""

import hmac
import hashlib
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


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
                "description": f"Assinatura Motogram GO — {motorista.nome_completo}",
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
        logger.error("MP_WEBHOOK_SECRET não configurado — rejeitando webhook")
        return False

    signature = request.headers.get("X-Signature", "")
    x_request_id = request.headers.get("X-Request-Id", "")

    if not signature or not x_request_id:
        logger.warning("Webhook sem X-Signature ou X-Request-Id")
        return False

    try:
        body = request.body.decode()
    except Exception:
        logger.warning("Webhook com body inválido")
        return False

    expected = hmac.new(
        secret.encode(),
        f"{x_request_id}{body}".encode(),
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
        assinatura = Assinatura.objects.get(mp_payment_id=str(payment_id), status="pendente")
    except Assinatura.DoesNotExist:
        try:
            assinatura = Assinatura.objects.get(pix_txid=str(payment_id), status="pendente")
        except Assinatura.DoesNotExist:
            return

    access_token = settings.MP_ACCESS_TOKEN
    if not access_token:
        logger.error("MP_ACCESS_TOKEN não configurado — não é possível verificar pagamento")
        return

    try:
        resp = requests.get(
            f"https://api.mercadopago.com/v1/payments/{payment_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("Falha ao consultar status do pagamento %s: HTTP %s", payment_id, resp.status_code)
            return
        payment_data = resp.json()
        if payment_data.get("status") != "approved":
            logger.info("Pagamento %s com status '%s' — não será activado", payment_id, payment_data.get("status"))
            return
    except requests.RequestException as e:
        logger.exception("Erro ao consultar API Mercado Pago para pagamento %s", payment_id)
        return

    activar_motorista_apos_pagamento(assinatura)
    logger.info("Assinatura %s activada após pagamento %s aprovado", assinatura.id, payment_id)
