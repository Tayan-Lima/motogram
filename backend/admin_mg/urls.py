import os
from django.urls import path
from . import views

PREFIX = os.environ.get("ADMIN_SECRET_PATH", "admin_mg")

app_name = "admin_mg"

urlpatterns = [
    path(f"{PREFIX}/", views.AdminDashboardView.as_view(), name="dashboard"),
    path(f"{PREFIX}/entrar/", views.AdminLoginView.as_view(), name="login"),
    path(f"{PREFIX}/sair/", views.AdminLogoutView.as_view(), name="logout"),

    # KYC — Cadastros
    path(f"{PREFIX}/cadastros/", views.CadastrosPendentesView.as_view(), name="cadastros_pendentes"),
    path(f"{PREFIX}/cadastros/<int:motorista_id>/analisar/", views.AnalisarCadastroView.as_view(), name="analisar_cadastro"),

    # CRM — Utilizadores
    path(f"{PREFIX}/motoristas/", views.MotoristasListView.as_view(), name="motoristas"),
    path(f"{PREFIX}/motoristas/<int:motorista_id>/", views.MotoristaDetailView.as_view(), name="motorista_detalhe"),
    path(f"{PREFIX}/passageiros/", views.PassageirosListView.as_view(), name="passageiros"),
    path(f"{PREFIX}/passageiros/<int:passageiro_id>/", views.PassageiroDetailView.as_view(), name="passageiro_detalhe"),

    # Dashboard — Corridas e Assinaturas
    path(f"{PREFIX}/corridas/", views.HistoricoCorridasView.as_view(), name="historico_corridas"),
    path(f"{PREFIX}/assinaturas/", views.AssinaturasDashboardView.as_view(), name="assinaturas"),
    path(f"{PREFIX}/avaliacoes/motoristas/", views.AvaliacoesMotoristasView.as_view(), name="avaliacoes_motoristas"),
    path(f"{PREFIX}/avaliacoes/passageiros/", views.AvaliacoesPassageirosView.as_view(), name="avaliacoes_passageiros"),
    path(f"{PREFIX}/avaliacoes/comentarios/", views.AvaliacoesComentariosView.as_view(), name="avaliacoes_comentarios"),
]
