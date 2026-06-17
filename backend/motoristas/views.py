"""Views da app motoristas — endpoints para verificação de assinatura e activação Telegram."""

import json
from django.http import JsonResponse
from django.views import View
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
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
                "message": "Motorista não registado.",
                "link": f"{settings.SITE_URL}/motorista/cadastro",
            })

        if motorista.assinatura_activa:
            return JsonResponse({"active": True})

        return JsonResponse({
            "active": False,
            "message": "Assinatura inactiva.",
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
        motorista.save()

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
            return render(request, "motorista/cadastro.html", {"erro": "E-mail já registado."})

        if Motorista.objects.filter(cpf=dados["cpf"]).exists():
            return render(request, "motorista/cadastro.html", {"erro": "CPF já registado."})

        if Motorista.objects.filter(placa=dados["placa"]).exists():
            return render(request, "motorista/cadastro.html", {"erro": "Placa já registada."})

        import secrets as _secrets
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


class LoginMotoristaView(View):
    """GET/POST /motorista/login/ — login do motorista."""

    def get(self, request):
        return render(request, "motorista/login.html")

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("/motorista/dashboard/")

        return render(request, "motorista/login.html", {"erro": "Credenciais inválidas."})


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
        from .services import notificar_motorista_telegram_private

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


class ContaMotoristaView(LoginRequiredMixin, View):
    """GET /motorista/conta/ — conta do motorista."""

    login_url = "/motorista/login/"

    def get(self, request):
        try:
            motorista = request.user.motorista
        except Motorista.DoesNotExist:
            return redirect("/motorista/cadastro/")

        return render(request, "motorista/conta.html", {"motorista": motorista})


class GerarLinkTelegramView(LoginRequiredMixin, View):
    """POST /motorista/gerar-link-telegram/ — gera link de activação Telegram."""

    login_url = "/motorista/login/"

    def post(self, request):
        try:
            motorista = request.user.motorista
        except Motorista.DoesNotExist:
            return JsonResponse({"erro": "Motorista não encontrado."}, status=404)

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
        import json
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
