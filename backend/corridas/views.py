"""Views da app corridas — endpoints para o bot e passageiro."""

import json
import threading
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils.decorators import method_decorator

from .models import Corrida
from .services import notificar_motoristas_proximos
from motoristas.models import Motorista


class BotAuthMixin:
    """Verifica o X-Bot-Secret header para endpoints internos."""

    def verificar_bot_secret(self, request):
        bot_secret = request.headers.get("X-Bot-Secret")
        if bot_secret != settings.BOT_SECRET:
            return JsonResponse({"erro": "Não autorizado"}, status=403)
        return None


class CriarCorridaView(BotAuthMixin, View):
    """POST /api/corridas/ — cria uma nova corrida (chamado pelo bot)."""

    def post(self, request):
        auth_erro = self.verificar_bot_secret(request)
        if auth_erro:
            return auth_erro

        import json
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido"}, status=400)

        passageiro_telegram_id = data.get("passageiro_telegram_id")
        origem_lat = data.get("origem_lat")
        origem_lon = data.get("origem_lon")

        if not all([passageiro_telegram_id, origem_lat, origem_lon]):
            return JsonResponse({"erro": "Campos obrigatórios em falta"}, status=400)

        from motoristas.models import Utilizador
        try:
            passageiro = Utilizador.objects.get(telegram_id=passageiro_telegram_id)
        except Utilizador.DoesNotExist:
            passageiro = Utilizador.objects.create_user(
                username=f"tg_{passageiro_telegram_id}",
                telegram_id=passageiro_telegram_id,
                tipo="passageiro",
            )

        corrida = Corrida.objects.create(
            passageiro=passageiro,
            origem_lat=origem_lat,
            origem_lon=origem_lon,
            destino_lat=data.get("destino_lat"),
            destino_lon=data.get("destino_lon"),
            status="aguardando",
        )

        # Notificar motoristas em background (não bloquear o request)
        threading.Thread(
            target=notificar_motoristas_proximos,
            args=(corrida,),
            daemon=True,
        ).start()

        return JsonResponse({
            "id": corrida.id,
            "status": corrida.status,
        }, status=201)


class AceitarCorridaView(BotAuthMixin, View):
    """POST /api/corridas/{id}/aceitar/ — motorista aceita corrida."""

    def post(self, request, corrida_id):
        auth_erro = self.verificar_bot_secret(request)
        if auth_erro:
            return auth_erro

        import json
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido"}, status=400)

        motorista_telegram_id = data.get("motorista_telegram_id")
        if not motorista_telegram_id:
            return JsonResponse({"erro": "motorista_telegram_id obrigatório"}, status=400)

        with transaction.atomic():
            corrida = Corrida.objects.select_for_update().get(
                id=corrida_id, status="aguardando"
            )

            try:
                motorista = Motorista.objects.get(telegram_id=motorista_telegram_id)
            except Motorista.DoesNotExist:
                return JsonResponse({"erro": "Motorista não encontrado"}, status=404)

            if not motorista.assinatura_activa:
                return JsonResponse({
                    "erro": "Assinatura inactiva.",
                    "link": f"{settings.SITE_URL}/motorista/conta",
                }, status=403)

            corrida.motorista = motorista
            corrida.status = "aceite"
            corrida.aceite_em = timezone.now()
            corrida.save()

        return JsonResponse({
            "id": corrida.id,
            "status": corrida.status,
            "passageiro": {
                "nome": corrida.passageiro.username,
                "telefone": corrida.passageiro.telefone or "N/A",
            },
            "origem": f"{corrida.origem_lat}, {corrida.origem_lon}",
        })


class RecusarCorridaView(BotAuthMixin, View):
    """POST /api/corridas/{id}/recusar/ — motorista recusa corrida."""

    def post(self, request, corrida_id):
        auth_erro = self.verificar_bot_secret(request)
        if auth_erro:
            return auth_erro

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido"}, status=400)

        motorista_telegram_id = data.get("motorista_telegram_id")
        if not motorista_telegram_id:
            return JsonResponse({"erro": "motorista_telegram_id obrigatório"}, status=400)

        corrida = get_object_or_404(Corrida, id=corrida_id, status="aguardando")

        # Tentar próximo motorista em vez de cancelar
        threading.Thread(
            target=notificar_motoristas_proximos,
            args=(corrida,),
            daemon=True,
        ).start()

        return JsonResponse({"id": corrida.id, "status": corrida.status})


class ConcluirCorridaView(BotAuthMixin, View):
    """POST /api/corridas/{id}/concluir/ — motorista conclui corrida."""

    def post(self, request, corrida_id):
        auth_erro = self.verificar_bot_secret(request)
        if auth_erro:
            return auth_erro

        import json
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido"}, status=400)

        motorista_telegram_id = data.get("motorista_telegram_id")
        if not motorista_telegram_id:
            return JsonResponse({"erro": "motorista_telegram_id obrigatório"}, status=400)

        corrida = get_object_or_404(Corrida, id=corrida_id, status="aceite")

        try:
            motorista = Motorista.objects.get(telegram_id=motorista_telegram_id)
        except Motorista.DoesNotExist:
            return JsonResponse({"erro": "Motorista não encontrado"}, status=404)

        if corrida.motorista != motorista:
            return JsonResponse({"erro": "Corrida não pertence a este motorista"}, status=403)

        corrida.status = "concluida"
        corrida.concluida_em = timezone.now()
        corrida.save()

        return JsonResponse({
            "id": corrida.id,
            "status": corrida.status,
            "valor": str(corrida.valor) if corrida.valor else "0.00",
            "distancia_km": corrida.distancia_km or 0,
        })


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CriarCorridaWebView(View):
    """POST /api/corridas/web/ — cria corrida pelo site (requer login)."""

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"erro": "Login obrigatório"}, status=401)
        if request.user.tipo != "passageiro":
            return JsonResponse({"erro": "Apenas passageiros podem pedir corrida"}, status=403)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido"}, status=400)

        origem_lat = data.get("origem_lat")
        origem_lon = data.get("origem_lon")

        if not origem_lat or not origem_lon:
            return JsonResponse({"erro": "Localização obrigatória"}, status=400)

        corrida = Corrida.objects.create(
            passageiro=request.user,
            origem_lat=origem_lat,
            origem_lon=origem_lon,
            destino_lat=data.get("destino_lat"),
            destino_lon=data.get("destino_lon"),
            status="aguardando",
        )

        threading.Thread(
            target=notificar_motoristas_proximos,
            args=(corrida,),
            daemon=True,
        ).start()

        return JsonResponse({
            "id": corrida.id,
            "status": corrida.status,
        }, status=201)


class CorridaStatusView(View):
    """GET /api/corridas/{id}/status/ — polling do passageiro."""

    def get(self, request, corrida_id):
        corrida = get_object_or_404(Corrida, id=corrida_id)

        if corrida.status == "aguardando":
            return JsonResponse({"status": "aguardando"})

        if corrida.status == "aceite":
            return JsonResponse({
                "status": "aceite",
                "motorista": {
                    "nome": corrida.motorista.nome_completo if corrida.motorista else "N/A",
                    "telefone": corrida.motorista.telefone if corrida.motorista else "N/A",
                    "moto": corrida.motorista.modelo_moto if corrida.motorista else "N/A",
                    "cor_moto": corrida.motorista.cor_moto if corrida.motorista else "N/A",
                },
            })

        return JsonResponse({"status": corrida.status})
