"""Views do painel admin — rota secreta."""

import os
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.conf import settings
from datetime import date, timedelta

from motoristas.models import Motorista, Utilizador
from corridas.models import Corrida
from pagamentos.models import Assinatura

PREFIX = os.environ.get("ADMIN_SECRET_PATH", "admin_mg")


class AdminMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = f"/{PREFIX}/entrar/"

    def test_func(self):
        return self.request.user.is_staff or self.request.user.tipo == "admin"

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(
                self.request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )
        raise Http404("Página não encontrada")


@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=False), name='dispatch')
class AdminLoginView(View):
    """GET/POST /{prefix}/entrar/ — login do admin."""

    def get(self, request):
        return render(request, "admin_mg/login.html", {"prefix": PREFIX})

    def post(self, request):
        if getattr(request, 'limited', False):
            return render(request, "admin_mg/login.html", {
                "prefix": PREFIX,
                "erro": "Muitas tentativas de login. Aguarde 1 minuto e tente novamente.",
            })
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user and (user.is_staff or user.tipo == "admin"):
            login(request, user)
            return redirect("admin_mg:dashboard")
        return render(request, "admin_mg/login.html", {
            "prefix": PREFIX,
            "erro": "Credenciais inválidas.",
        })


class AdminLogoutView(AdminMixin, View):
    """POST /{prefix}/sair/ — logout do admin."""

    def post(self, request):
        logout(request)
        return redirect("admin_mg:login")


class AdminDashboardView(AdminMixin, View):
    def get(self, request):
        motoristas_total = Motorista.objects.count()
        motoristas_pendentes = Motorista.objects.filter(status_cadastro="pendente").count()
        motoristas_activos = Motorista.objects.filter(activo=True).count()
        corridas_hoje = Corrida.objects.filter(criada_em__date=timezone.now().date()).count()
        corridas_total = Corrida.objects.count()

        agora = timezone.now()
        receita_mes = Corrida.objects.filter(
            concluida_em__year=agora.year,
            concluida_em__month=agora.month,
            status="concluida",
        ).aggregate(total=Sum("valor"))["total"] or 0

        assinaturas_activas = Assinatura.objects.filter(status="paga").count()
        mrr = assinaturas_activas * (settings.PRECO_ASSINATURA_MENSAL / 100.0)

        assinaturas_vencendo = Motorista.objects.filter(
            activo=True,
            assinatura_ate__lte=date.today() + timedelta(days=7),
            assinatura_ate__gte=date.today(),
        ).count()

        corridas_7_dias = []
        max_count = 0
        for i in range(6, -1, -1):
            dia = (timezone.now() - timedelta(days=i)).date()
            count = Corrida.objects.filter(criada_em__date=dia).count()
            corridas_7_dias.append({"dia": dia.strftime("%d/%m"), "count": count})
            if count > max_count:
                max_count = count

        context = {
            "prefix": PREFIX,
            "motoristas_total": motoristas_total,
            "motoristas_pendentes": motoristas_pendentes,
            "motoristas_activos": motoristas_activos,
            "corridas_hoje": corridas_hoje,
            "corridas_total": corridas_total,
            "receita_mes": receita_mes,
            "assinaturas_activas": assinaturas_activas,
            "mrr": mrr,
            "assinaturas_vencendo": assinaturas_vencendo,
            "corridas_7_dias": corridas_7_dias,
            "max_corridas_dia": max_count,
        }
        return render(request, "admin_mg/dashboard.html", context)


class CadastrosPendentesView(AdminMixin, View):
    def get(self, request):
        qs = Motorista.objects.filter(
            status_cadastro__in=["pendente", "em_analise"]
        )

        busca = request.GET.get("q", "").strip()
        if busca:
            qs = qs.filter(
                Q(nome_completo__icontains=busca)
                | Q(cpf__icontains=busca)
                | Q(telefone__icontains=busca)
                | Q(cidade__icontains=busca)
                | Q(placa__icontains=busca)
            )

        qs = qs.order_by("criado_em")
        paginator = Paginator(qs, 10)
        page = request.GET.get("p", 1)
        motoristas = paginator.get_page(page)

        return render(request, "admin_mg/cadastros_pendentes.html", {
            "motoristas": motoristas,
            "busca": busca,
            "prefix": PREFIX,
        })


class AnalisarCadastroView(AdminMixin, View):
    def post(self, request, motorista_id):
        motorista = get_object_or_404(Motorista, id=motorista_id)
        accao = request.POST.get("accao")

        if accao == "aprovar":
            motorista.status_cadastro = "aprovado"
            motorista.analisado_por = request.user
            motorista.analisado_em = timezone.now()
            motorista.save()
            _notificar_telegram_aprovado(motorista)

        elif accao == "reprovar":
            motivo = request.POST.get("motivo", "")
            motorista.status_cadastro = "reprovado"
            motorista.motivo_reprovacao = motivo
            motorista.analisado_por = request.user
            motorista.analisado_em = timezone.now()
            motorista.save()
            _notificar_telegram_reprovado(motorista, motivo)

        elif accao == "bloquear":
            motorista.activo = False
            motorista.status_cadastro = "suspenso"
            motorista.save()
            motorista.utilizador.is_active = False
            motorista.utilizador.save()

        elif accao == "reactivar":
            motorista.activo = True
            motorista.status_cadastro = "aprovado"
            motorista.save()
            motorista.utilizador.is_active = True
            motorista.utilizador.save()

        elif accao == "activar_manual":
            motorista.activo = True
            motorista.assinatura_ate = date.today() + timedelta(days=30)
            motorista.status_cadastro = "aprovado"
            motorista.save()

        elif accao == "excluir":
            utilizador = motorista.utilizador
            motorista.delete()
            utilizador.delete()
            return redirect("admin_mg:motoristas")

        return redirect(request.META.get("HTTP_REFERER", "admin_mg:motoristas"))


class HistoricoCorridasView(AdminMixin, View):
    def get(self, request):
        qs = Corrida.objects.select_related("passageiro", "motorista").all()

        busca = request.GET.get("q", "").strip()
        if busca:
            qs = qs.filter(
                Q(passageiro__email__icontains=busca)
                | Q(motorista__nome_completo__icontains=busca)
                | Q(destino_texto__icontains=busca)
                | Q(status__icontains=busca)
            )

        qs = qs.order_by("-criada_em")
        paginator = Paginator(qs, 25)
        page = request.GET.get("p", 1)
        corridas = paginator.get_page(page)

        return render(request, "admin_mg/historico_corridas.html", {
            "corridas": corridas,
            "busca": busca,
            "prefix": PREFIX,
        })


class MotoristasListView(AdminMixin, View):
    def get(self, request):
        qs = Motorista.objects.select_related("utilizador").all()

        busca = request.GET.get("q", "").strip()
        if busca:
            qs = qs.filter(
                Q(nome_completo__icontains=busca)
                | Q(cpf__icontains=busca)
                | Q(telefone__icontains=busca)
                | Q(cidade__icontains=busca)
                | Q(placa__icontains=busca)
                | Q(utilizador__email__icontains=busca)
            )

        qs = qs.order_by("-criado_em")
        paginator = Paginator(qs, 20)
        page = request.GET.get("p", 1)
        motoristas = paginator.get_page(page)

        return render(request, "admin_mg/motoristas.html", {
            "motoristas": motoristas,
            "busca": busca,
            "prefix": PREFIX,
        })


class MotoristaDetailView(AdminMixin, View):
    """GET /{prefix}/motoristas/{id}/ — perfil detalhado do motorista."""

    def get(self, request, motorista_id):
        motorista = get_object_or_404(Motorista.objects.select_related("utilizador"), id=motorista_id)
        corridas = Corrida.objects.filter(motorista=motorista).order_by("-criada_em")[:20]
        assinaturas = Assinatura.objects.filter(motorista=motorista).order_by("-criada_em")

        cpf_valido = validar_cpf(motorista.cpf) if motorista.cpf else None

        return render(request, "admin_mg/motorista_detalhe.html", {
            "motorista": motorista,
            "corridas": corridas,
            "assinaturas": assinaturas,
            "cpf_valido": cpf_valido,
            "prefix": PREFIX,
        })


class PassageirosListView(AdminMixin, View):
    """GET /{prefix}/passageiros/ — lista de passageiros."""

    def get(self, request):
        qs = Utilizador.objects.filter(tipo="passageiro")

        busca = request.GET.get("q", "").strip()
        if busca:
            qs = qs.filter(
                Q(email__icontains=busca)
                | Q(username__icontains=busca)
                | Q(telefone__icontains=busca)
            )

        qs = qs.order_by("-date_joined")
        paginator = Paginator(qs, 20)
        page = request.GET.get("p", 1)
        passageiros = paginator.get_page(page)

        return render(request, "admin_mg/passageiros.html", {
            "passageiros": passageiros,
            "busca": busca,
            "prefix": PREFIX,
        })


class PassageiroDetailView(AdminMixin, View):
    """GET/POST /{prefix}/passageiros/{id}/ — perfil detalhado do passageiro."""

    def get(self, request, passageiro_id):
        passageiro = get_object_or_404(Utilizador, id=passageiro_id, tipo="passageiro")
        corridas = Corrida.objects.filter(passageiro=passageiro).order_by("-criada_em")[:20]
        total_gasto = Corrida.objects.filter(
            passageiro=passageiro, status="concluida"
        ).aggregate(total=Sum("valor"))["total"] or 0

        return render(request, "admin_mg/passageiro_detalhe.html", {
            "passageiro": passageiro,
            "corridas": corridas,
            "total_gasto": total_gasto,
            "prefix": PREFIX,
        })

    def post(self, request, passageiro_id):
        passageiro = get_object_or_404(Utilizador, id=passageiro_id, tipo="passageiro")
        accao = request.POST.get("accao")

        if accao == "suspender":
            passageiro.is_active = False
            passageiro.save()

        elif accao == "reativar":
            passageiro.is_active = True
            passageiro.save()

        elif accao == "excluir":
            passageiro.delete()
            return redirect("admin_mg:passageiros")

        return redirect("admin_mg:passageiro_detalhe", passageiro_id=passageiro_id)


class AssinaturasDashboardView(AdminMixin, View):
    """GET /{prefix}/assinaturas/ — dashboard de assinaturas."""

    def get(self, request):
        assinaturas_activas = Assinatura.objects.filter(status="paga").count()
        assinaturas_pendentes = Assinatura.objects.filter(status="pendente").count()
        mrr = assinaturas_activas * (settings.PRECO_ASSINATURA_MENSAL / 100.0)

        vencendo_7 = Motorista.objects.filter(
            activo=True,
            assinatura_ate__lte=date.today() + timedelta(days=7),
            assinatura_ate__gte=date.today(),
        )
        vencendo_15 = Motorista.objects.filter(
            activo=True,
            assinatura_ate__lte=date.today() + timedelta(days=15),
            assinatura_ate__gt=date.today() + timedelta(days=7),
        )
        expiradas = Motorista.objects.filter(
            assinatura_ate__lt=date.today(),
        ).exclude(activo=False)

        receita_total = Assinatura.objects.filter(status="paga").aggregate(
            total=Sum("valor")
        )["total"] or 0

        return render(request, "admin_mg/assinaturas.html", {
            "assinaturas_activas": assinaturas_activas,
            "assinaturas_pendentes": assinaturas_pendentes,
            "mrr": mrr,
            "receita_total": receita_total,
            "vencendo_7": vencendo_7,
            "vencendo_15": vencendo_15,
            "expiradas": expiradas,
            "prefix": PREFIX,
        })


def validar_cpf(cpf: str) -> bool:
    """Valida CPF pelo algoritmo dos dígitos verificadores (open-source, sem API externa)."""
    if not cpf:
        return False

    cpf = ''.join(filter(str.isdigit, cpf))

    if len(cpf) != 11:
        return False

    if cpf == cpf[0] * 11:
        return False

    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    digito1 = resto if resto < 10 else 0

    if digito1 != int(cpf[9]):
        return False

    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    digito2 = resto if resto < 10 else 0

    return digito2 == int(cpf[10])


def _notificar_telegram_aprovado(motorista):
    if not motorista.telegram_id:
        return
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": motorista.telegram_id,
                "text": (
                    f"✅ *Cadastro aprovado!*\n\n"
                    f"Parabéns, {motorista.nome_completo}!\n"
                    f"O teu cadastro foi aprovado.\n"
                    f"Já podes receber corridas!"
                ),
                "parse_mode": "Markdown",
            },
            timeout=5,
        )
    except Exception:
        pass


def _notificar_telegram_reprovado(motorista, motivo):
    if not motorista.telegram_id:
        return
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": motorista.telegram_id,
                "text": (
                    f"❌ *Cadastro não aprovado*\n\n"
                    f"Olá, {motorista.nome_completo}.\n"
                    f"Infelizmente não conseguimos aprovar o teu cadastro.\n\n"
                    f"Motivo: {motivo}\n\n"
                    f"Corrige os dados e reenvia em:\n"
                    f"{settings.SITE_URL}/motorista/cadastro/"
                ),
                "parse_mode": "Markdown",
            },
            timeout=5,
        )
    except Exception:
        pass


class AvaliacoesMotoristasView(AdminMixin, View):
    def get(self, request):
        from django.db.models import Avg
        dias = request.GET.get("dias", "90")
        try:
            dias = int(dias)
        except ValueError:
            dias = 90
        desde = timezone.now() - timedelta(days=dias)
        motoristas = Motorista.objects.filter(
            utilizador__avaliacoes_recebidas__criada_em__gte=desde,
            utilizador__avaliacoes_recebidas__tipo='pm',
        ).annotate(
            media=Avg("utilizador__avaliacoes_recebidas__nota"),
            total_avaliacoes=Count("utilizador__avaliacoes_recebidas"),
        ).order_by("media")
        return render(request, "admin_mg/avaliacoes_motoristas.html", {
            "prefix": PREFIX, "motoristas": motoristas, "dias": dias,
        })


class AvaliacoesPassageirosView(AdminMixin, View):
    def get(self, request):
        from django.db.models import Avg
        dias = request.GET.get("dias", "90")
        try:
            dias = int(dias)
        except ValueError:
            dias = 90
        desde = timezone.now() - timedelta(days=dias)
        passageiros = Utilizador.objects.filter(
            avaliacoes_recebidas__criada_em__gte=desde,
            avaliacoes_recebidas__tipo='mp',
        ).annotate(
            media=Avg("avaliacoes_recebidas__nota"),
            total_avaliacoes=Count("avaliacoes_recebidas"),
        ).order_by("media")
        return render(request, "admin_mg/avaliacoes_passageiros.html", {
            "prefix": PREFIX, "passageiros": passageiros, "dias": dias,
        })


class AvaliacoesComentariosView(AdminMixin, View):
    def get(self, request):
        from corridas.models import Avaliacao
        dias = request.GET.get("dias", "90")
        try:
            dias = int(dias)
        except ValueError:
            dias = 90
        desde = timezone.now() - timedelta(days=dias)
        comentarios = Avaliacao.objects.filter(
            comentario__gt="",
            criada_em__gte=desde,
        ).select_related("corrida", "avaliador", "avaliado").order_by("-criada_em")
        return render(request, "admin_mg/avaliacoes_comentarios.html", {
            "prefix": PREFIX, "comentarios": comentarios, "dias": dias,
        })
