"""Views do painel admin customizado."""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils import timezone
from django.db.models import Sum, Count
from django.core.mail import send_mail
from django.conf import settings

from motoristas.models import Motorista
from corridas.models import Corrida


class AdminMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin para verificar se o utilizador é admin."""

    login_url = "/motorista/login/"

    def test_func(self):
        return self.request.user.is_staff or self.request.user.tipo == "admin"


class AdminDashboardView(AdminMixin, View):
    """GET /admin_mg/ — dashboard admin."""

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
            "motoristas_total": motoristas_total,
            "motoristas_pendentes": motoristas_pendentes,
            "motoristas_activos": motoristas_activos,
            "corridas_hoje": corridas_hoje,
            "corridas_total": corridas_total,
            "receita_mes": receita_mes,
        }
        return render(request, "admin_mg/dashboard.html", context)


class CadastrosPendentesView(AdminMixin, View):
    """GET /admin_mg/cadastros/ — lista de cadastros pendentes."""

    def get(self, request):
        motoristas = Motorista.objects.filter(
            status_cadastro__in=["pendente", "em_analise"]
        ).order_by("criado_em")
        return render(request, "admin_mg/cadastros_pendentes.html", {"motoristas": motoristas})


class AnalisarCadastroView(AdminMixin, View):
    """POST /admin_mg/cadastros/{id}/analisar/ — aprovar ou reprovar."""

    def post(self, request, motorista_id):
        motorista = get_object_or_404(Motorista, id=motorista_id)
        accao = request.POST.get("accao")

        if accao == "aprovar":
            motorista.status_cadastro = "aprovado"
            motorista.analisado_por = request.user
            motorista.analisado_em = timezone.now()
            motorista.save()
            self._notificar_aprovado(motorista)

        elif accao == "reprovar":
            motivo = request.POST.get("motivo", "")
            motorista.status_cadastro = "reprovado"
            motorista.motivo_reprovacao = motivo
            motorista.analisado_por = request.user
            motorista.analisado_em = timezone.now()
            motorista.save()
            self._notificar_reprovado(motorista, motivo)

        return redirect("admin_mg:cadastros_pendentes")

    def _notificar_aprovado(self, motorista):
        if not motorista.utilizador.email:
            return
        try:
            send_mail(
                subject="✅ MotoGram — Cadastro aprovado!",
                message=(
                    f"Parabéns, {motorista.nome_completo}!\n\n"
                    f"O teu cadastro foi aprovado. Já podes pagar a assinatura e começar a receber corridas.\n\n"
                    f"Acede agora: {settings.SITE_URL}/motorista/conta/\n\n"
                    f"Equipa MotoGram"
                ),
                from_email="noreply@motogram.app",
                recipient_list=[motorista.utilizador.email],
                fail_silently=True,
            )
        except Exception:
            pass

    def _notificar_reprovado(self, motorista, motivo):
        if not motorista.utilizador.email:
            return
        try:
            send_mail(
                subject="❌ MotoGram — Cadastro não aprovado",
                message=(
                    f"Olá, {motorista.nome_completo}.\n\n"
                    f"Infelizmente não conseguimos aprovar o teu cadastro.\n\n"
                    f"Motivo: {motivo}\n\n"
                    f"Podes corrigir e reenviar os documentos em:\n"
                    f"{settings.SITE_URL}/motorista/cadastro/\n\n"
                    f"Equipa MotoGram"
                ),
                from_email="noreply@motogram.app",
                recipient_list=[motorista.utilizador.email],
                fail_silently=True,
            )
        except Exception:
            pass


class HistoricoCorridasView(AdminMixin, View):
    """GET /admin_mg/corridas/ — histórico de corridas."""

    def get(self, request):
        corridas = Corrida.objects.all().order_by("-criada_em")[:100]
        return render(request, "admin_mg/historico_corridas.html", {"corridas": corridas})


class MotoristasListView(AdminMixin, View):
    """GET /admin_mg/motoristas/ — lista de motoristas."""

    def get(self, request):
        motoristas = Motorista.objects.all().order_by("-criado_em")
        return render(request, "admin_mg/motoristas.html", {"motoristas": motoristas})
