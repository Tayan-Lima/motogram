"""Views da app corridas — endpoints para o bot e passageiro."""

import html
import json
import logging
import threading
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db import transaction
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
            origem_texto=data.get("origem_texto", ""),
            destino_lat=data.get("destino_lat"),
            destino_lon=data.get("destino_lon"),
            destino_texto=data.get("destino_texto", ""),
            ponto_referencia=data.get("ponto_referencia", ""),
            valor_sugerido=data.get("valor_sugerido"),
            status="aguardando",
        )

        threading.Thread(
            target=notificar_motoristas_proximos,
            args=(corrida,),
            daemon=False,
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

        if not request.user.email_confirmado:
            return JsonResponse({
                "erro": "Confirma o teu e-mail antes de pedir corrida. Verifica a tua caixa de entrada.",
                "link": "/passageiro/perfil/",
            }, status=403)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido"}, status=400)

        origem_lat = data.get("origem_lat")
        origem_lon = data.get("origem_lon")
        origem_texto = (data.get("origem_texto") or "").strip()

        if not origem_lat or not origem_lon:
            return JsonResponse({"erro": "Localização de origem obrigatória"}, status=400)

        destino_texto = (data.get("destino_texto") or "").strip()
        destino_lat = data.get("destino_lat")
        destino_lon = data.get("destino_lon")

        if not destino_texto:
            return JsonResponse({"erro": "Destino obrigatório. Indica para onde queres ir."}, status=400)

        corrida = Corrida.objects.create(
            passageiro=request.user,
            origem_lat=origem_lat,
            origem_lon=origem_lon,
            origem_texto=origem_texto,
            destino_lat=destino_lat,
            destino_lon=destino_lon,
            destino_texto=destino_texto,
            ponto_referencia=data.get("ponto_referencia", ""),
            valor_sugerido=data.get("valor_sugerido"),
            status="aguardando",
        )

        threading.Thread(
            target=notificar_motoristas_proximos,
            args=(corrida,),
            daemon=False,
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
                "erro": "Assinatura inativa ou cadastro pendente.",
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
                "erro": "Assinatura inativa ou cadastro pendente.",
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

        corrida = get_object_or_404(Corrida.objects.select_related("motorista", "passageiro"), id=corrida_id)
        if corrida.status not in ("aceite", "em_curso"):
            return JsonResponse({"erro": "Corrida não está em estado que permite conclusão."}, status=400)

        try:
            motorista = Motorista.objects.get(telegram_id=motorista_telegram_id)
        except Motorista.DoesNotExist:
            return JsonResponse({"erro": "Motorista não encontrado"}, status=404)

        if corrida.motorista != motorista:
            return JsonResponse({"erro": "Corrida não pertence a este motorista"}, status=403)

        # Calcular distância se não definida
        if not corrida.distancia_km and corrida.destino_lat:
            from .services import calcular_distancia_km
            corrida.distancia_km = calcular_distancia_km(
                corrida.origem_lat, corrida.origem_lon,
                corrida.destino_lat, corrida.destino_lon,
            )

        corrida.status = "concluida"
        corrida.concluida_em = timezone.now()
        corrida.save()

        # Notificar passageiro
        if corrida.passageiro.telegram_id:
            from .services import notificar_passageiro_telegram
            valor_str = f"R$ {corrida.valor}" if corrida.valor else "combinado"
            threading.Thread(
                target=notificar_passageiro_telegram,
                args=(corrida.passageiro.telegram_id,
                      f"✅ <b>Corrida concluída!</b>\n\n"
                      f"Valor: {valor_str}\n"
                      f"Distância: {corrida.distancia_km or '?'} km\n\n"
                      f"Obrigado por usar o Motogram GO! 🏍️"),
                daemon=False,
            ).start()

        return JsonResponse({
            "id": corrida.id,
            "status": corrida.status,
            "valor": str(corrida.valor) if corrida.valor else "0.00",
            "distancia_km": corrida.distancia_km or 0,
        })


class IniciarCorridaView(BotAuthMixin, View):
    """POST /api/corridas/{id}/iniciar/ — motorista inicia a corrida."""

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

        corrida = get_object_or_404(Corrida.objects.select_related("motorista", "passageiro"), id=corrida_id, status="aceite")

        try:
            motorista = Motorista.objects.get(telegram_id=motorista_telegram_id)
        except Motorista.DoesNotExist:
            return JsonResponse({"erro": "Motorista não encontrado"}, status=404)

        if corrida.motorista != motorista:
            return JsonResponse({"erro": "Corrida não pertence a este motorista"}, status=403)

        corrida.status = "em_curso"
        corrida.iniciada_em = timezone.now()
        corrida.save()

        # Notificar passageiro
        if corrida.passageiro.telegram_id:
            from .services import notificar_passageiro_telegram
            threading.Thread(
                target=notificar_passageiro_telegram,
                args=(corrida.passageiro.telegram_id,
                      f"🏍️ <b>{motorista.nome_completo}</b> iniciou a corrida e está a caminho!\n\n"
                      f"Moto: {motorista.modelo_moto} {motorista.cor_moto}\n"
                      f"Placa: {motorista.placa}"),
                daemon=False,
            ).start()

        return JsonResponse({"ok": True, "corrida_id": corrida.id, "status": "em_curso"})


class CancelarCorridaMotoristaView(BotAuthMixin, View):
    """POST /api/corridas/{id}/cancelar-motorista/ — motorista cancela a corrida."""

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

        corrida = get_object_or_404(Corrida.objects.select_related("motorista", "passageiro"), id=corrida_id)
        if corrida.status not in ("aceite", "em_curso"):
            return JsonResponse({"erro": "Corrida não pode ser cancelada neste estado."}, status=400)

        try:
            motorista = Motorista.objects.get(telegram_id=motorista_telegram_id)
        except Motorista.DoesNotExist:
            return JsonResponse({"erro": "Motorista não encontrado"}, status=404)

        if corrida.motorista != motorista:
            return JsonResponse({"erro": "Corrida não pertence a este motorista"}, status=403)

        corrida.status = "cancelada"
        corrida.save()

        # Notificar passageiro
        if corrida.passageiro.telegram_id:
            from .services import notificar_passageiro_telegram
            threading.Thread(
                target=notificar_passageiro_telegram,
                args=(corrida.passageiro.telegram_id,
                      f"❌ <b>{motorista.nome_completo}</b> cancelou a corrida.\n\n"
                      "Podes pedir outra corrida no site. 🏍️"),
                daemon=False,
            ).start()

        return JsonResponse({"ok": True, "corrida_id": corrida.id, "status": "cancelada"})


@method_decorator(login_required, name='dispatch')
class ListarOfertasView(View):
    """GET /api/corridas/{id}/ofertas/ — passageiro vê motoristas que responderam."""

    def get(self, request, corrida_id):
        corrida = get_object_or_404(Corrida, id=corrida_id)
        if corrida.passageiro_id != request.user.id:
            return JsonResponse({"erro": "Acesso negado."}, status=403)

        ofertas = corrida.ofertas.filter(status="pendente").select_related("motorista__utilizador")

        resultado = []
        for o in ofertas:
            m = o.motorista
            resultado.append({
                "id": o.id,
                "motorista_id": m.id,
                "nome": m.nome_completo,
                "valor": float(o.valor),
                "tipo": o.tipo,
                "moto": m.modelo_moto,
                "cor_moto": m.cor_moto,
                "media_avaliacoes": m.utilizador.media_avaliacoes,
                "total_corridas": m.utilizador.total_corridas_concluidas,
            })

        return JsonResponse({
            "corrida_id": corrida.id,
            "status": corrida.status,
            "ofertas": resultado,
        })


@method_decorator(login_required, name='dispatch')
class EscolherMotoristaView(View):
    """POST /api/corridas/{id}/escolher/ — passageiro escolhe um motorista."""

    def post(self, request, corrida_id):
        corrida = get_object_or_404(Corrida, id=corrida_id, status="aguardando")
        if corrida.passageiro_id != request.user.id:
            return JsonResponse({"erro": "Acesso negado."}, status=403)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido"}, status=400)

        oferta_id = data.get("oferta_id")
        if not oferta_id:
            return JsonResponse({"erro": "oferta_id obrigatório"}, status=400)

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
            daemon=False,
        ).start()

        motorista = oferta.motorista

        return JsonResponse({
            "ok": True,
            "corrida_id": corrida.id,
            "status": corrida.status,
            "motorista": {
                "nome": motorista.nome_completo,
                "moto": motorista.modelo_moto,
                "cor_moto": motorista.cor_moto,
                "telefone": motorista.telefone,
            },
        })


class CorridaStatusView(View):
    """GET /api/corridas/{id}/status/ — polling do passageiro."""

    def get(self, request, corrida_id):
        corrida = get_object_or_404(Corrida.objects.select_related("motorista__utilizador"), id=corrida_id)

        if corrida.status == "aguardando":
            qtd_ofertas = corrida.ofertas.filter(status="pendente").count()
            return JsonResponse({"status": "aguardando", "ofertas": qtd_ofertas})

        response = {"status": corrida.status}

        from .models import Avaliacao
        if corrida.passageiro and corrida.status == "concluida":
            response["avaliado"] = Avaliacao.objects.filter(
                corrida=corrida, tipo='pm'
            ).exists()

        if corrida.motorista:
            m = corrida.motorista
            foto_url = m.utilizador.foto.url if m.utilizador.foto else None
            response["motorista"] = {
                "nome": m.nome_completo or "N/A",
                "telefone": m.telefone or "N/A",
                "moto": m.modelo_moto or "N/A",
                "cor_moto": m.cor_moto or "N/A",
                "foto_url": foto_url,
            }

        if corrida.status == "concluida":
            response["valor"] = str(corrida.valor) if corrida.valor else None
            response["distancia_km"] = corrida.distancia_km

        return JsonResponse(response)


@method_decorator(login_required, name='dispatch')
class CancelarCorridaView(View):
    """POST /api/corridas/{id}/cancelar/ — passageiro cancela corrida aguardando."""

    def post(self, request, corrida_id):
        corrida = get_object_or_404(
            Corrida.objects.prefetch_related("ofertas__motorista"), id=corrida_id
        )

        if corrida.status not in ("aguardando",):
            return JsonResponse({"erro": "Não é possível cancelar uma corrida que já foi aceite."}, status=400)

        if corrida.passageiro_id != request.user.id:
            return JsonResponse({"erro": "Esta corrida não te pertence."}, status=403)

        corrida.status = "cancelada"
        corrida.save()

        from .services import notificar_motorista_telegram
        for oferta in corrida.ofertas.filter(status="pendente"):
            m = oferta.motorista
            if m and m.telegram_id:
                threading.Thread(
                    target=notificar_motorista_telegram,
                    args=(m.telegram_id, "❌ O passageiro cancelou a corrida.", None),
                    daemon=True,
                ).start()

        return JsonResponse({"ok": True, "status": "cancelada"})


def _mascarar_telefone(telefone: str) -> str:
    if not telefone or len(telefone) < 4:
        return "****"
    return "****-" + telefone[-4:]


def _notificar_resultado_ofertas(corrida):
    from .services import notificar_motorista_telegram, enviar_localizacao_telegram, \
        _extrair_message_id

    logger = logging.getLogger(__name__)

    for oferta in corrida.ofertas.all():
        motorista = oferta.motorista
        if not motorista.telegram_id:
            continue

        try:
            tg_str = str(motorista.telegram_id)
            msg_ids = []

            if oferta.status == "aceita":
                r1 = enviar_localizacao_telegram(motorista.telegram_id, corrida.origem_lat, corrida.origem_lon)
                mid = _extrair_message_id(r1)
                if mid:
                    msg_ids.append(mid)

                if corrida.destino_lat and corrida.destino_lon:
                    r2 = enviar_localizacao_telegram(motorista.telegram_id, corrida.destino_lat, corrida.destino_lon)
                    mid = _extrair_message_id(r2)
                    if mid:
                        msg_ids.append(mid)

                nome_passageiro = html.escape(corrida.passageiro.first_name or corrida.passageiro.username)
                origem = html.escape(corrida.endereco_origem)
                destino = html.escape(corrida.endereco_destino)
                telefone = _mascarar_telefone(corrida.passageiro.telefone or '')

                msg = (
                    "<b>Corrida confirmada!</b>\n\n"
                    f"Valor: R$ {oferta.valor}\n"
                    f"Passageiro: {nome_passageiro}\n"
                    f"Contacto: {telefone}\n"
                    f"Origem: {origem}\n"
                    f"Destino: {destino}\n"
                )
                if corrida.ponto_referencia:
                    msg += f"Ref: {html.escape(corrida.ponto_referencia)}\n"
                msg += "\nBoa corrida! 🏍️"

                reply_markup = {
                    "inline_keyboard": [
                        [
                            {"text": "🏍️ Iniciar corrida", "callback_data": f"iniciar:{corrida.id}"},
                        ],
                        [
                            {"text": "❌ Cancelar corrida", "callback_data": f"cancelar_motorista:{corrida.id}"},
                        ],
                    ]
                }
            else:
                msg = "🤷 O passageiro escolheu outro motorista."
                reply_markup = None

            resultado = notificar_motorista_telegram(motorista.telegram_id, msg, reply_markup)
            mid = _extrair_message_id(resultado)
            if mid:
                msg_ids.append(mid)

            if msg_ids:
                if tg_str not in corrida.notificacao_msg_ids:
                    corrida.notificacao_msg_ids[tg_str] = []
                corrida.notificacao_msg_ids[tg_str].extend(msg_ids)
                try:
                    corrida.save(update_fields=["notificacao_msg_ids"])
                except Exception:
                    pass

            if resultado and resultado.get("ok"):
                logger.info(
                    "Resultado oferta enviado para motorista %s (tg=%s) — corrida %s status=%s",
                    motorista.nome_completo, motorista.telegram_id, corrida.id, oferta.status,
                )
            else:
                logger.warning(
                    "Falha ao notificar resultado oferta motorista %s (tg=%s): %s",
                    motorista.nome_completo, motorista.telegram_id, resultado,
                )
        except Exception:
            logger.exception(
                "Erro ao notificar resultado oferta motorista %s (tg=%s) — corrida %s",
                motorista.nome_completo, motorista.telegram_id, corrida.id,
            )


class AvaliarMotoristaView(View):
    """POST /api/corridas/{id}/avaliar/ — passageiro avalia o motorista."""

    def post(self, request, corrida_id):
        if not request.user.is_authenticated:
            return JsonResponse({"erro": "Login obrigatório."}, status=401)

        corrida = get_object_or_404(
            Corrida.objects.select_related("motorista__utilizador", "passageiro"), id=corrida_id
        )

        if corrida.passageiro_id != request.user.id:
            return JsonResponse({"erro": "Esta corrida não te pertence."}, status=403)

        if corrida.status != "concluida":
            return JsonResponse({"erro": "Só podes avaliar corridas concluídas."}, status=400)

        if not corrida.motorista:
            return JsonResponse({"erro": "Esta corrida não tem motorista."}, status=400)

        from .models import Avaliacao
        if Avaliacao.objects.filter(corrida=corrida, tipo='pm').exists():
            return JsonResponse({"erro": "Já avaliaste esta corrida."}, status=400)

        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = {}

        nota = data.get("nota")
        if not isinstance(nota, int) or nota < 1 or nota > 5:
            return JsonResponse({"erro": "Nota deve ser entre 1 e 5."}, status=400)

        comentario = data.get("comentario", "").strip()[:500] if nota <= 2 else ""

        Avaliacao.objects.create(
            corrida=corrida,
            avaliador=request.user,
            avaliado=corrida.motorista.utilizador,
            tipo='pm',
            nota=nota,
            comentario=comentario,
        )

        return JsonResponse({"ok": True})


class AvaliarPassageiroView(BotAuthMixin, View):
    """POST /api/corridas/{id}/avaliar-passageiro/ — motorista avalia o passageiro."""

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

        corrida = get_object_or_404(
            Corrida.objects.select_related("motorista__utilizador", "passageiro"), id=corrida_id
        )

        if corrida.status != "concluida":
            return JsonResponse({"erro": "Só podes avaliar corridas concluídas."}, status=400)

        try:
            motorista = Motorista.objects.get(telegram_id=motorista_telegram_id)
        except Motorista.DoesNotExist:
            return JsonResponse({"erro": "Motorista não encontrado"}, status=404)

        if corrida.motorista != motorista:
            return JsonResponse({"erro": "Corrida não pertence a este motorista"}, status=403)

        from .models import Avaliacao

        nota = data.get("nota")
        comentario = data.get("comentario", "").strip()[:500] if data.get("comentario") else ""

        if nota is not None:
            if not isinstance(nota, int) or nota < 1 or nota > 5:
                return JsonResponse({"erro": "Nota deve ser entre 1 e 5."}, status=400)

            av, _ = Avaliacao.objects.get_or_create(
                corrida=corrida,
                tipo='mp',
                defaults={
                    'avaliador': motorista.utilizador,
                    'avaliado': corrida.passageiro,
                    'nota': nota,
                    'comentario': comentario,
                },
            )

            if comentario and not av.comentario:
                av.comentario = comentario
                av.save(update_fields=["comentario"])

        elif comentario:
            try:
                av = Avaliacao.objects.get(corrida=corrida, tipo='mp')
                av.comentario = comentario
                av.save(update_fields=["comentario"])
            except Avaliacao.DoesNotExist:
                return JsonResponse({"erro": "Avaliação não encontrada. Envia a nota primeiro."}, status=400)

        return JsonResponse({"ok": True})
