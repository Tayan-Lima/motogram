"""Views da app motoristas — endpoints para verificação de assinatura e activação Telegram."""

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Utilizador, Motorista
from .services import validar_token_telegram, gerar_token_telegram
from .validators import validar_documento, validar_imagem
from motogram.mixins import BotAuthMixin


class VerificarAssinaturaView(BotAuthMixin, View):
    """GET /api/motoristas/verificar-assinatura/ — chamado pelo bot."""

    def get(self, request):
        auth_erro = self.verificar_bot_secret(request)
        if auth_erro:
            return auth_erro

        telegram_id = request.GET.get("telegram_id")
        if not telegram_id:
            return JsonResponse({"active": False, "message": "telegram_id obrigatório"}, status=400)

        try:
            motorista = Motorista.objects.get(telegram_id=int(telegram_id))
        except (ValueError, Motorista.DoesNotExist):
            return JsonResponse({
                "active": False,
                "message": "Motorista não registrado.",
                "link": f"{settings.SITE_URL}/motorista/cadastro",
            })

        if motorista.assinatura_activa:
            return JsonResponse({"active": True})

        return JsonResponse({
            "active": False,
            "message": "Assinatura inativa.",
            "link": f"{settings.SITE_URL}/motorista/conta",
        })


class MotoristasProximosView(BotAuthMixin, View):
    """GET /api/motoristas/proximos/ — busca motoristas num raio."""

    def get(self, request):
        auth_erro = self.verificar_bot_secret(request)
        if auth_erro:
            return auth_erro

        lat = request.GET.get("lat")
        lon = request.GET.get("lon")
        try:
            raio = float(request.GET.get("raio", 5))
        except (ValueError, TypeError):
            raio = 5

        if not lat or not lon:
            return JsonResponse({"erro": "lat e lon obrigatórios"}, status=400)

        from django.contrib.gis.geos import Point
        from django.contrib.gis.db.models.functions import Distance
        from django.contrib.gis.measure import D

        ponto = Point(float(lon), float(lat), srid=4326)

        motoristas = Motorista.objects.filter(
            activo=True,
            status_cadastro="aprovado",
            telegram_id__isnull=False,
            localizacao__isnull=False,
        ).annotate(
            distancia=Distance("localizacao", ponto)
        ).filter(
            distancia__lte=D(km=raio)
        ).order_by("distancia")[:5]

        resultado = []
        for m in motoristas:
            resultado.append({
                "id": m.id,
                "nome": m.nome_completo,
                "telefone": m.telefone,
                "modelo_moto": m.modelo_moto,
                "distancia_km": round(m.distancia.km, 1) if m.distancia else None,
            })

        return JsonResponse(resultado, safe=False)


class ActivarTelegramView(BotAuthMixin, View):
    """POST /api/motoristas/activar-telegram/ — activa Telegram com token."""

    def post(self, request):
        from datetime import timedelta
        from django.db import IntegrityError
        from django.utils import timezone

        auth_erro = self.verificar_bot_secret(request)
        if auth_erro:
            return auth_erro

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido"}, status=400)

        token = data.get("token")
        telegram_id = data.get("telegram_id")

        if not token or not telegram_id:
            return JsonResponse({"erro": "token e telegram_id obrigatórios"}, status=400)

        motorista = validar_token_telegram(token)
        if not motorista:
            return JsonResponse({"erro": "Token inválido ou expirado."}, status=400)

        motorista.telegram_id = telegram_id
        try:
            motorista.save()
        except IntegrityError:
            motorista.telegram_token = token
            motorista.telegram_token_expiry = timezone.now() + timedelta(hours=24)
            motorista.telegram_id = None
            motorista.save()
            return JsonResponse({
                "erro": "Este Telegram já está vinculado a outro motorista.",
            }, status=409)

        return JsonResponse({
            "ok": True,
            "motorista": motorista.nome_completo,
        })


class CadastroMotoristaView(View):
    """GET/POST /motorista/cadastro/ — cadastro de novo motorista."""

    def get(self, request):
        return render(request, "motorista/cadastro.html")

    def post(self, request):
        dados = {
            "nome_completo": request.POST.get("nome_completo", "").strip(),
            "cpf": request.POST.get("cpf", "").strip(),
            "data_nascimento": request.POST.get("data_nascimento", "").strip(),
            "telefone": request.POST.get("telefone", "").strip(),
            "email": request.POST.get("email", "").strip(),
            "cidade": request.POST.get("cidade", "").strip(),
            "modelo_moto": request.POST.get("modelo_moto", "").strip(),
            "ano_moto": request.POST.get("ano_moto", "").strip(),
            "cor_moto": request.POST.get("cor_moto", "").strip(),
            "placa": request.POST.get("placa", "").strip(),
            "consumo_km_l": request.POST.get("consumo_km_l", "35").strip(),
        }

        faltando = []
        if not dados["nome_completo"]:
            faltando.append("Nome completo")
        if not dados["cpf"]:
            faltando.append("CPF")
        if not dados["data_nascimento"]:
            faltando.append("Data de nascimento")
        if not dados["telefone"]:
            faltando.append("Telefone")
        if not dados["email"]:
            faltando.append("E-mail")
        if not dados["cidade"]:
            faltando.append("Cidade")
        if not dados["modelo_moto"]:
            faltando.append("Modelo da moto")
        if not dados["ano_moto"]:
            faltando.append("Ano da moto")
        if not dados["cor_moto"]:
            faltando.append("Cor da moto")
        if not dados["placa"]:
            faltando.append("Placa")
        if faltando:
            return render(request, "motorista/cadastro.html", {
                "erro": f"Preencha todos os campos obrigatórios: {', '.join(faltando)}.",
            })

        try:
            ano_moto = int(dados["ano_moto"])
        except (ValueError, TypeError):
            return render(request, "motorista/cadastro.html", {
                "erro": "Ano da moto inválido. Digite um número (ex: 2020).",
            })

        try:
            consumo_km_l = float(dados["consumo_km_l"]) if dados["consumo_km_l"] else 35.0
        except (ValueError, TypeError):
            consumo_km_l = 35.0

        if Utilizador.objects.filter(email=dados["email"]).exists():
            return render(request, "motorista/cadastro.html", {"erro": "E-mail já registrado."})

        if Motorista.objects.filter(cpf=dados["cpf"]).exists():
            return render(request, "motorista/cadastro.html", {"erro": "CPF já registrado."})

        if Motorista.objects.filter(placa=dados["placa"]).exists():
            return render(request, "motorista/cadastro.html", {"erro": "Placa já registrada."})

        if Motorista.objects.filter(telefone=dados["telefone"]).exists():
            return render(request, "motorista/cadastro.html", {"erro": "Telefone já registrado."})

        if Utilizador.objects.filter(telefone=dados["telefone"]).exists():
            return render(request, "motorista/cadastro.html", {"erro": "Telefone já registrado."})

        password = request.POST.get("password", "").strip()
        password_confirm = request.POST.get("password_confirm", "").strip()

        if not password:
            return render(request, "motorista/cadastro.html", {
                "erro": "Cria uma senha para a tua conta.",
            })
        if len(password) < 6:
            return render(request, "motorista/cadastro.html", {
                "erro": "A senha deve ter pelo menos 6 caracteres.",
            })
        if password != password_confirm:
            return render(request, "motorista/cadastro.html", {
                "erro": "As senhas não coincidem. Verifica e tenta de novo.",
            })

        utilizador = Utilizador.objects.create_user(
            username=dados["email"],
            email=dados["email"],
            password=password,
            tipo="motorista",
            telefone=dados["telefone"],
        )

        motorista = Motorista.objects.create(
            utilizador=utilizador,
            nome_completo=dados["nome_completo"],
            cpf=dados["cpf"],
            data_nascimento=dados["data_nascimento"],
            telefone=dados["telefone"],
            cidade=dados["cidade"],
            modelo_moto=dados["modelo_moto"],
            ano_moto=ano_moto,
            cor_moto=dados["cor_moto"],
            placa=dados["placa"],
            consumo_km_l=consumo_km_l,
        )

        erros_validacao = []
        for campo, validator_func in [
            ("cnh_frente", validar_documento),
            ("cnh_verso", validar_documento),
            ("antecedentes", validar_documento),
            ("foto_rosto", validar_imagem),
        ]:
            ficheiro = request.FILES.get(campo)
            if ficheiro:
                try:
                    validator_func(ficheiro)
                except Exception as e:
                    erros_validacao.append(str(e))

        if erros_validacao:
            utilizador.delete()
            return render(request, "motorista/cadastro.html", {
                "erro": " ".join(erros_validacao),
            })

        if request.FILES.get("cnh_frente"):
            motorista.cnh_frente = request.FILES["cnh_frente"]
        if request.FILES.get("cnh_verso"):
            motorista.cnh_verso = request.FILES["cnh_verso"]
        if request.FILES.get("antecedentes"):
            motorista.antecedentes = request.FILES["antecedentes"]
        if request.FILES.get("foto_rosto"):
            motorista.foto_rosto = request.FILES["foto_rosto"]
        motorista.save()

        login(request, utilizador)
        return redirect("/motorista/dashboard/")


@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=False), name='dispatch')
class LoginMotoristaView(View):
    """GET/POST /motorista/login/ — login do motorista."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("/motorista/dashboard/")
        return render(request, "motorista/login.html")

    def post(self, request):
        if getattr(request, 'limited', False):
            return render(request, "motorista/login.html", {
                "erro": "Muitas tentativas de login. Aguarde 1 minuto e tente novamente.",
            })
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is not None and user.tipo == "motorista":
            login(request, user)
            return redirect("/motorista/dashboard/")

        if user is None and username:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("Falha de login motorista: username=%r", username)

        return render(request, "motorista/login.html", {
            "erro": "Credenciais inválidas.",
            "username": username,
        })


class LogoutMotoristaView(View):
    """POST /motorista/logout/ — logout do motorista."""

    def post(self, request):
        logout(request)
        return redirect("/")


class RecuperarSenhaMotoristaView(View):
    """GET/POST /motorista/recuperar-senha/ — recuperação de senha do motorista."""

    def get(self, request):
        return render(request, "motorista/recuperar_senha.html")

    def post(self, request):
        import secrets

        email = request.POST.get("email", "").strip().lower()

        if not email:
            return render(request, "motorista/recuperar_senha.html", {
                "erro": "Informa o teu e-mail.",
                "email": email,
            })

        try:
            utilizador = Utilizador.objects.get(email=email, tipo="motorista")
        except Utilizador.DoesNotExist:
            return render(request, "motorista/recuperar_senha.html", {"enviado": True})

        nova_senha = secrets.token_urlsafe(8)
        utilizador.set_password(nova_senha)
        utilizador.save()

        try:
            motorista = utilizador.motorista
            if motorista.telegram_id:
                from corridas.services import notificar_motorista_telegram
                notificar_motorista_telegram(
                    motorista.telegram_id,
                    f"🔑 *Nova senha*\n\nA tua nova senha é: `{nova_senha}`\n\nGuarda-a e troca depois no site.\n{motorista_login_url()}",
                )
        except Exception:
            pass

        return render(request, "motorista/recuperar_senha.html", {"enviado": True})


def motorista_login_url():
    from django.conf import settings
    site = getattr(settings, "SITE_URL", "http://localhost:8000")
    return f"{site}/motorista/login/"


class DashboardMotoristaView(LoginRequiredMixin, View):
    """GET /motorista/dashboard/ — dashboard do motorista."""

    login_url = "/motorista/login/"

    def get(self, request):
        try:
            motorista = request.user.motorista
        except Motorista.DoesNotExist:
            return redirect("/motorista/cadastro/")

        from corridas.models import Corrida
        from django.db.models import Sum
        from datetime import date, timedelta

        hoje = date.today()
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        inicio_mes = hoje.replace(day=1)

        corridas_hoje = Corrida.objects.filter(
            motorista=motorista,
            concluida_em__date=hoje,
            status="concluida",
        )
        corridas_semana = Corrida.objects.filter(
            motorista=motorista,
            concluida_em__date__gte=inicio_semana,
            status="concluida",
        )
        corridas_mes = Corrida.objects.filter(
            motorista=motorista,
            concluida_em__date__gte=inicio_mes,
            status="concluida",
        )

        corridas_recentes = Corrida.objects.filter(
            motorista=motorista,
        ).order_by("-criada_em")[:5]

        context = {
            "motorista": motorista,
            "ganhos_hoje": corridas_hoje.aggregate(total=Sum("valor"))["total"] or 0,
            "corridas_hoje": corridas_hoje.count(),
            "ganhos_semana": corridas_semana.aggregate(total=Sum("valor"))["total"] or 0,
            "ganhos_mes": corridas_mes.aggregate(total=Sum("valor"))["total"] or 0,
            "corridas_recentes": corridas_recentes,
        }
        return render(request, "motorista/dashboard.html", context)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class ContaMotoristaView(LoginRequiredMixin, View):
    """GET /motorista/conta/ — conta do motorista."""

    login_url = "/motorista/login/"

    def get(self, request):
        try:
            motorista = request.user.motorista
        except Motorista.DoesNotExist:
            return redirect("/motorista/cadastro/")

        return render(request, "motorista/conta.html", {"motorista": motorista})


class DesconectarTelegramView(LoginRequiredMixin, View):
    """POST /motorista/desconectar-telegram/ — desvincula Telegram do motorista."""

    login_url = "/motorista/login/"

    def post(self, request):
        try:
            motorista = request.user.motorista
        except Motorista.DoesNotExist:
            return JsonResponse({"erro": "Motorista não encontrado."}, status=404)

        motorista.telegram_id = None
        motorista.telegram_token = None
        motorista.telegram_token_expiry = None
        motorista.save()
        motorista.utilizador.telegram_id = None
        motorista.utilizador.save(update_fields=["telegram_id"])

        return JsonResponse({"ok": True})


class GerarLinkTelegramView(LoginRequiredMixin, View):
    """POST /motorista/gerar-link-telegram/ — gera link de activação Telegram."""

    login_url = "/motorista/login/"

    def post(self, request):
        try:
            motorista = request.user.motorista
        except Motorista.DoesNotExist:
            return JsonResponse({"erro": "Motorista não encontrado."}, status=404)

        if motorista.status_cadastro != "aprovado":
            return JsonResponse({
                "erro": "O teu cadastro ainda não foi aprovado. Aguarda a verificação dos documentos.",
            }, status=403)

        if not motorista.assinatura_activa:
            return JsonResponse({
                "erro": "Precisas de uma assinatura ativa para ativar o Telegram. Pague a assinatura primeiro.",
                "link": "/motorista/conta/",
            }, status=403)

        if motorista.telegram_id:
            return JsonResponse({
                "erro": "O teu Telegram já está ativado.",
            }, status=400)

        token = gerar_token_telegram(motorista)
        link = f"https://t.me/MotoGram_Go_bot?start={token}"

        return JsonResponse({"link": link, "token": token})


class HistoricoMotoristaView(LoginRequiredMixin, View):
    """GET /motorista/historico/ — histórico de corridas do motorista."""

    login_url = "/motorista/login/"

    def get(self, request):
        try:
            motorista = request.user.motorista
        except Motorista.DoesNotExist:
            return redirect("/motorista/cadastro/")

        from corridas.models import Corrida
        corridas = Corrida.objects.filter(
            motorista=motorista,
        ).order_by("-criada_em")[:50]

        return render(request, "motorista/historico.html", {"corridas": corridas})


class AssinaturaMotoristaView(LoginRequiredMixin, View):
    """GET /motorista/assinatura/ — página de assinatura."""

    login_url = "/motorista/login/"

    def get(self, request):
        return render(request, "motorista/assinatura.html")


class ToggleOnlineView(LoginRequiredMixin, View):
    """POST /api/motoristas/toggle-online/ — alterna estado activo do motorista."""

    login_url = "/motorista/login/"

    def post(self, request):
        try:
            motorista = request.user.motorista
        except Motorista.DoesNotExist:
            return JsonResponse({"erro": "Motorista não encontrado."}, status=404)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = {}

        if "activo" in data:
            motorista.activo = data["activo"]
        else:
            motorista.activo = not motorista.activo

        motorista.save()
        return JsonResponse({"activo": motorista.activo})


class EditarPerfilMotoristaView(LoginRequiredMixin, View):
    """GET/POST /motorista/editar-perfil/ — editar informações não sensíveis."""

    login_url = "/motorista/login/"

    CAMPOS_EDITAVEIS = ["telefone", "email", "cidade", "modelo_moto", "ano_moto", "cor_moto"]

    def get(self, request):
        try:
            motorista = request.user.motorista
        except Motorista.DoesNotExist:
            return redirect("/motorista/cadastro/")

        return render(request, "motorista/editar_perfil.html", {"motorista": motorista})

    def post(self, request):
        try:
            motorista = request.user.motorista
        except Motorista.DoesNotExist:
            return JsonResponse({"erro": "Motorista não encontrado."}, status=404)

        dados = {k: request.POST.get(k, "").strip() for k in self.CAMPOS_EDITAVEIS}

        erros = []

        novo_email = dados["email"].lower()
        if novo_email and novo_email != motorista.utilizador.email:
            if Utilizador.objects.filter(email=novo_email).exists():
                erros.append("E-mail já registrado por outro usuário.")
            else:
                motorista.utilizador.email = novo_email
                motorista.utilizador.username = novo_email

        novo_telefone = dados["telefone"]
        if novo_telefone and novo_telefone != motorista.telefone:
            if Motorista.objects.filter(telefone=novo_telefone).exists():
                erros.append("Telefone já registrado por outro motorista.")
            else:
                motorista.telefone = novo_telefone
                motorista.utilizador.telefone = novo_telefone

        if dados["cidade"]:
            motorista.cidade = dados["cidade"]
        if dados["modelo_moto"]:
            motorista.modelo_moto = dados["modelo_moto"]
        if dados["cor_moto"]:
            motorista.cor_moto = dados["cor_moto"]

        if dados["ano_moto"]:
            try:
                motorista.ano_moto = int(dados["ano_moto"])
            except (ValueError, TypeError):
                erros.append("Ano da moto inválido.")

        if erros:
            return render(request, "motorista/editar_perfil.html", {
                "motorista": motorista,
                "erro": " ".join(erros),
            })

        motorista.save()
        motorista.utilizador.save()

        return render(request, "motorista/editar_perfil.html", {
            "motorista": motorista,
            "sucesso": "Perfil actualizado com sucesso.",
        })


class UploadFotoMotoristaView(LoginRequiredMixin, View):
    """POST /motorista/upload-foto/ — upload da foto de perfil do motorista."""

    login_url = "/motorista/login/"

    def post(self, request):
        try:
            motorista = request.user.motorista
        except Motorista.DoesNotExist:
            return JsonResponse({"erro": "Motorista não encontrado."}, status=404)

        foto = request.FILES.get("foto")
        if not foto:
            return JsonResponse({"erro": "Nenhuma foto enviada."}, status=400)

        if not foto.content_type or not foto.content_type.startswith("image/"):
            return JsonResponse({"erro": "Formato inválido. Use JPG ou PNG."}, status=400)

        if foto.size > 5 * 1024 * 1024:
            return JsonResponse({"erro": "Foto muito grande. Máximo 5MB."}, status=400)

        try:
            from PIL import Image
            img = Image.open(foto)
            img.thumbnail((200, 200), Image.LANCZOS)
            if img.mode == "RGBA":
                img = img.convert("RGB")
            import io
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            buf.seek(0)
            from django.core.files.base import ContentFile
            motorista.utilizador.foto.save(
                f"{motorista.utilizador.username}_profile.jpg",
                ContentFile(buf.read()),
                save=False,
            )
        except Exception:
            return JsonResponse({"erro": "Erro ao processar a imagem."}, status=400)

        motorista.utilizador.save(update_fields=["foto"])
        return JsonResponse({"ok": True, "foto_url": motorista.utilizador.foto.url})


class LimparMensagensView(BotAuthMixin, View):
    """POST /api/motoristas/limpar-mensagens/ — motorista limpa mensagens antigas do chat."""

    def post(self, request):
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

        try:
            motorista = Motorista.objects.get(telegram_id=motorista_telegram_id)
        except Motorista.DoesNotExist:
            return JsonResponse({"erro": "Motorista não encontrado"}, status=404)

        from corridas.models import Corrida
        from corridas.services import _token
        import requests

        tg_str = str(motorista_telegram_id)
        token = _token()
        if not token:
            return JsonResponse({"erro": "Configuração Telegram não encontrada"}, status=500)

        corridas = Corrida.objects.filter(notificacao_msg_ids__has_key=tg_str).order_by("-id")

        apagadas = 0
        for corrida in corridas[3:]:
            msg_ids = corrida.notificacao_msg_ids.get(tg_str, [])
            if msg_ids:
                for i in range(0, len(msg_ids), 100):
                    batch = msg_ids[i:i + 100]
                    try:
                        requests.post(
                            f"https://api.telegram.org/bot{token}/deleteMessages",
                            json={"chat_id": motorista_telegram_id, "message_ids": batch},
                            timeout=10,
                        )
                        apagadas += len(batch)
                    except Exception:
                        pass
                corrida.notificacao_msg_ids.pop(tg_str, None)
                corrida.save(update_fields=["notificacao_msg_ids"])

        # Limpeza agressiva — apagar mensagens com IDs sequenciais (não tracked)
        all_ids = []
        for c in corridas[:3]:
            all_ids.extend(c.notificacao_msg_ids.get(tg_str, []))
        max_tracked = max(all_ids) if all_ids else 200
        import threading
        from corridas.services import _limpeza_agressiva
        threading.Thread(
            target=_limpeza_agressiva,
            args=(motorista_telegram_id, max_tracked - 2),
            daemon=True,
        ).start()

        return JsonResponse({"ok": True, "apagadas": apagadas, "limpeza_fundo": True})
