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
from django.db.models import F
from django.utils.decorators import method_decorator

from .models import Corrida, Oferta
from .services import notificar_motoristas_proximos
from motoristas.models import Motorista, Utilizador
from motogram.mixins import BotAuthMixin


class CriarCorridaView(BotAuthMixin, View):
    """POST /api/corridas/ — cria corrida (chamado pelo bot, mantido para compatibilidade)."""

    def post(self, request):
        auth_erro = self.verificar_bot_secret(request)
        if auth_erro:
            return auth_erro

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido"}, status=400)

        passageiro_telegram_id = data.get("passageiro_telegram_id")
        origem_lat = data.get("origem_lat")
        origem_lon = data.get("origem_lon")

        if not all([passageiro_telegram_id, origem_lat, origem_lon]):
            return JsonResponse({"erro": "Campos obrigatórios em falta"}, status=400)

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
            ponto_referencia=data.get("ponto_referencia", ""),
            valor_sugerido=data.get("valor_sugerido"),
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
            ponto_referencia=data.get("ponto_referencia", ""),
            valor_sugerido=data.get("valor_sugerido"),
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


class AceitarCorridaView(BotAuthMixin, View):
    """POST /api/corridas/{id}/aceitar/ — motorista aceita o valor sugerido pelo passageiro."""

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

        try:
            motorista = Motorista.objects.get(telegram_id=motorista_telegram_id)
        except Motorista.DoesNotExist:
            return JsonResponse({"erro": "Motorista não encontrado"}, status=404)

        if not motorista.pode_receber_corridas:
            return JsonResponse({
                "erro": "Assinatura inactiva ou cadastro pendente.",
            }, status=403)

        if Oferta.objects.filter(corrida=corrida, motorista=motorista).exists():
            return JsonResponse({"erro": "Já fizeste uma oferta nesta corrida"}, status=400)

        Oferta.objects.create(
            corrida=corrida,
            motorista=motorista,
            valor=corrida.valor_sugerido or 0,
            tipo="aceite",
        )

        return JsonResponse({
            "ok": True,
            "corrida_id": corrida.id,
        })


class CriarOfertaView(BotAuthMixin, View):
    """POST /api/corridas/{id}/ofertar/ — motorista faz contra-oferta."""

    def post(self, request, corrida_id):
        auth_erro = self.verificar_bot_secret(request)
        if auth_erro:
            return auth_erro

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido"}, status=400)

        motorista_telegram_id = data.get("motorista_telegram_id")
        valor = data.get("valor")

        if not motorista_telegram_id or not valor:
            return JsonResponse({"erro": "motorista_telegram_id e valor obrigatórios"}, status=400)

        corrida = get_object_or_404(Corrida, id=corrida_id, status="aguardando")

        try:
            motorista = Motorista.objects.get(telegram_id=motorista_telegram_id)
        except Motorista.DoesNotExist:
            return JsonResponse({"erro": "Motorista não encontrado"}, status=404)

        if not motorista.pode_receber_corridas:
            return JsonResponse({
                "erro": "Assinatura inactiva ou cadastro pendente.",
            }, status=403)

        if Oferta.objects.filter(corrida=corrida, motorista=motorista).exists():
            return JsonResponse({"erro": "Já fizeste uma oferta nesta corrida"}, status=400)

        Oferta.objects.create(
            corrida=corrida,
            motorista=motorista,
            valor=valor,
            tipo="contra_oferta",
        )

        return JsonResponse({
            "ok": True,
            "corrida_id": corrida.id,
            "valor": float(valor),
        })


class RecusarCorridaView(BotAuthMixin, View):
    """POST /api/corridas/{id}/recusar/ — motorista recusa."""

    def post(self, request, corrida_id):
        auth_erro = self.verificar_bot_secret(request)
        if auth_erro:
            return auth_erro

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido"}, status=400)

        return JsonResponse({"ok": True, "corrida_id": corrida_id})


class ConcluirCorridaView(BotAuthMixin, View):
    """POST /api/corridas/{id}/concluir/ — motorista conclui corrida."""

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


class ListarOfertasView(View):
    """GET /api/corridas/{id}/ofertas/ — passageiro vê motoristas que responderam."""

    def get(self, request, corrida_id):
        corrida = get_object_or_404(Corrida, id=corrida_id)

        ofertas = corrida.ofertas.filter(status="pendente").select_related("motorista")

        resultado = []
        for o in ofertas:
            resultado.append({
                "id": o.id,
                "motorista_id": o.motorista.id,
                "nome": o.motorista.nome_completo,
                "valor": float(o.valor),
                "tipo": o.tipo,
                "moto": o.motorista.modelo_moto,
                "cor_moto": o.motorista.cor_moto,
            })

        return JsonResponse({
            "corrida_id": corrida.id,
            "status": corrida.status,
            "ofertas": resultado,
        })


class EscolherMotoristaView(View):
    """POST /api/corridas/{id}/escolher/ — passageiro escolhe um motorista."""

    def post(self, request, corrida_id):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido"}, status=400)

        oferta_id = data.get("oferta_id")
        if not oferta_id:
            return JsonResponse({"erro": "oferta_id obrigatório"}, status=400)

        corrida = get_object_or_404(Corrida, id=corrida_id, status="aguardando")

        with transaction.atomic():
            oferta = get_object_or_404(
                Oferta.objects.select_for_update(),
                id=oferta_id,
                corrida=corrida,
                status="pendente",
            )

            oferta.status = "aceita"
            oferta.save()

            Oferta.objects.filter(corrida=corrida, status="pendente").update(
                status="rejeitada"
            )

            corrida.motorista = oferta.motorista
            corrida.status = "aceite"
            corrida.valor = oferta.valor
            corrida.aceite_em = timezone.now()
            corrida.save()

        threading.Thread(
            target=_notificar_resultado_ofertas,
            args=(corrida,),
            daemon=True,
        ).start()

        motorista = oferta.motorista
        telefone_mascarado = _mascarar_telefone(motorista.telefone or "")

        return JsonResponse({
            "ok": True,
            "corrida_id": corrida.id,
            "status": corrida.status,
            "motorista": {
                "nome": motorista.nome_completo,
                "moto": motorista.modelo_moto,
                "cor_moto": motorista.cor_moto,
                "telefone": telefone_mascarado,
            },
        })


class CorridaStatusView(View):
    """GET /api/corridas/{id}/status/ — polling do passageiro."""

    def get(self, request, corrida_id):
        corrida = get_object_or_404(Corrida, id=corrida_id)

        if corrida.status == "aguardando":
            qtd_ofertas = corrida.ofertas.filter(status="pendente").count()
            return JsonResponse({"status": "aguardando", "ofertas": qtd_ofertas})

        if corrida.status == "aceite":
            m = corrida.motorista
            return JsonResponse({
                "status": "aceite",
                "motorista": {
                    "nome": m.nome_completo if m else "N/A",
                    "telefone": _mascarar_telefone(m.telefone or "") if m else "N/A",
                    "moto": m.modelo_moto if m else "N/A",
                    "cor_moto": m.cor_moto if m else "N/A",
                },
            })

        return JsonResponse({"status": corrida.status})


def _mascarar_telefone(telefone: str) -> str:
    if not telefone or len(telefone) < 4:
        return "****"
    return "****-" + telefone[-4:]


def _notificar_resultado_ofertas(corrida):
    from .services import notificar_motorista_telegram

    for oferta in corrida.ofertas.all():
        motorista = oferta.motorista
        if not motorista.telegram_id:
            continue

        if oferta.status == "aceita":
            nome_passageiro = corrida.passageiro.first_name or corrida.passageiro.username
            msg = (
                f"🎉 *Corrida confirmada!*\n\n"
                f"💰 Valor: R$ {oferta.valor}\n"
                f"👤 Passageiro: {nome_passageiro}\n"
                f"📞 Contacto: {_mascarar_telefone(corrida.passageiro.telefone or '')}\n"
                f"📍 Origem: {corrida.origem_lat:.4f}, {corrida.origem_lon:.4f}\n"
            )
            if corrida.destino_lat:
                msg += f"📍 Destino: {corrida.destino_lat:.4f}, {corrida.destino_lon:.4f}\n"
            if corrida.ponto_referencia:
                msg += f"📍 Ref: {corrida.ponto_referencia}\n"
            msg += "\nBoa corrida! 🏍️"
            reply_markup = {
                "inline_keyboard": [[
                    {"text": "✅ Concluir corrida", "callback_data": f"concluir:{corrida.id}"},
                ]]
            }
        else:
            msg = "🤷 O passageiro escolheu outro motorista."
            reply_markup = None

        notificar_motorista_telegram(motorista.telegram_id, msg, reply_markup)
