"""Views da app pagamentos — criação de assinatura e webhook Mercado Pago."""

import json
import hmac
import hashlib
import uuid
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Assinatura
from .services import criar_pix_mercadopago
from motoristas.services import activar_motorista_apos_pagamento
from motoristas.models import Motorista


class CriarAssinaturaView(LoginRequiredMixin, View):
    """POST /api/assinaturas/criar/ — gera QR Code Pix."""

    login_url = "/motorista/login/"

    def post(self, request):
        try:
            motorista = request.user.motorista
        except Motorista.DoesNotExist:
            return JsonResponse({"erro": "Motorista não encontrado."}, status=404)

        if motorista.assinatura_activa:
            return JsonResponse({
                "erro": "Já tens uma assinatura activa.",
                "valida_ate": motorista.assinatura_ate.isoformat(),
            }, status=400)

        valor = settings.PRECO_ASSINATURA_MENSAL
        pix_txid = str(uuid.uuid4())

        assinatura = Assinatura.objects.create(
            motorista=motorista,
            valor=valor / 100.0,  # centavos → reais
            pix_txid=pix_txid,
            status="pendente",
        )

        # Gerar QR Code Pix via Mercado Pago
        pix_data = criar_pix_mercadopago(motorista, valor, pix_txid)

        return JsonResponse({
            "id": assinatura.id,
            "status": assinatura.status,
            "valor": float(assinatura.valor),
            "pix_copia_cola": pix_data.get("pix_copia_cola", ""),
            "qr_code_base64": pix_data.get("qr_code_base64", ""),
        }, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class WebhookMercadoPagoView(View):
    """POST /api/webhook/mercadopago/ — confirmação de pagamento Pix."""

    def verificar_assinatura(self, request):
        """Verifica assinatura HMAC do webhook Mercado Pago."""
        secret = settings.MP_WEBHOOK_SECRET
        if not secret:
            return True  # Sem secret configurado, aceitar (desenvolvimento)

        signature = request.headers.get("X-Signature", "")
        x_request_id = request.headers.get("X-Request-Id", "")

        # Gerar assinatura esperada
        expected = hmac.new(
            secret.encode(),
            f"{x_request_id}{request.body.decode()}".encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    def post(self, request):
        if not self.verificar_assinatura(request):
            return JsonResponse({"erro": "Assinatura inválida"}, status=403)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido"}, status=400)

        payment_id = data.get("data", {}).get("id")
        payment_type = data.get("type")

        if payment_type != "payment" or not payment_id:
            return JsonResponse({"ok": True})

        try:
            assinatura = Assinatura.objects.get(pix_txid=payment_id, status="pendente")
        except Assinatura.DoesNotExist:
            return JsonResponse({"ok": True})

        activar_motorista_apos_pagamento(assinatura)

        return JsonResponse({"ok": True})
