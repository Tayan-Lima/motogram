"""Views da app pagamentos — criação de assinatura e webhook Mercado Pago."""

import json
import uuid
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Assinatura
from .services import criar_pix_mercadopago, verificar_assinatura_webhook, processar_webhook_mercadopago
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
                "erro": "Já tem uma assinatura ativa.",
                "valida_ate": motorista.assinatura_ate.isoformat(),
            }, status=400)

        valor = settings.PRECO_ASSINATURA_MENSAL
        pix_txid = str(uuid.uuid4())

        assinatura = Assinatura.objects.create(
            motorista=motorista,
            valor=valor / 100.0,
            pix_txid=pix_txid,
            status="pendente",
        )

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

    def post(self, request):
        if not verificar_assinatura_webhook(request):
            return JsonResponse({"erro": "Assinatura inválida"}, status=403)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido"}, status=400)

        processar_webhook_mercadopago(data)

        return JsonResponse({"ok": True})
