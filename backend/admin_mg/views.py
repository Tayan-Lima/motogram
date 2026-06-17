"""Views do painel admin — rota secreta."""

import os
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from django.views import View
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils import timezone
from django.db.models import Sum, Count
from django.conf import settings

from motoristas.models import Motorista
from corridas.models import Corrida

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


class AdminLoginView(View):
    """GET/POST /{prefix}/entrar/ — login do admin."""

    def get(self, request):
        return render(request, "admin_mg/login.html", {"prefix": PREFIX})

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user and (user.is_staff or user.tipo == "admin"):
            login(request, user)
            return redirect("admin_mg:dashboard")
        return render(request, "admin_mg/login.html", {
            "prefix": PREFIX,
            "erro": "Credenciais inválidas ou sem permissão de administrador.",
        })


class AdminDashboardView(AdminMixin, View):
    def get(self, request):
        motoristas_total = Motorista.objects.count()
        motoristas_pendentes = Motorista.objects.filter(status_cadastro="pendente").count()
        motoristas_activos = Motorista.objects.filter(activo=True).count()
        corridas_hoje = Corrida.objects.filter(criada_em__date=timezone.now().date()).count()
        corridas_total = Corrida.objects.count()
        receita_mes = Corrida.objects.filter(
            concluida_em__month=timezone.now().month,
            status="concluida",
        ).aggregate(total=Sum("valor"))["total"] or 0

        context = {
            "prefix": PREFIX,
            "motoristas_total": motoristas_total,
            "motoristas_pendentes": motoristas_pendentes,
            "motoristas_activos": motoristas_activos,
            "corridas_hoje": corridas_hoje,
            "corridas_total": corridas_total,
            "receita_mes": receita_mes,
        }
        return render(request, "admin_mg/dashboard.html", context)


class CadastrosPendentesView(AdminMixin, View):
    def get(self, request):
        motoristas = Motorista.objects.filter(
            status_cadastro__in=["pendente", "em_analise"]
        ).order_by("criado_em")
        return render(request, "admin_mg/cadastros_pendentes.html", {
            "motoristas": motoristas,
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

        elif accao == "suspender":
            motorista.status_cadastro = "suspenso"
            motorista.activo = False
            motorista.save()

        elif accao == "reactivar":
            motorista.status_cadastro = "aprovado"
            motorista.save()

        return redirect("admin_mg:cadastros_pendentes")


class HistoricoCorridasView(AdminMixin, View):
    def get(self, request):
        corridas = Corrida.objects.all().order_by("-criada_em")[:100]
        return render(request, "admin_mg/historico_corridas.html", {
            "corridas": corridas,
            "prefix": PREFIX,
        })


class MotoristasListView(AdminMixin, View):
    def get(self, request):
        motoristas = Motorista.objects.all().order_by("-criado_em")
        return render(request, "admin_mg/motoristas.html", {
            "motoristas": motoristas,
            "prefix": PREFIX,
        })


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
