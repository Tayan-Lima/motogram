from django.urls import path
from . import views, bot_webhook as bot_views

app_name = "motoristas"

urlpatterns = [
    # API endpoints (bot communication)
    path("api/motoristas/verificar-assinatura/", views.VerificarAssinaturaView.as_view(), name="verificar_assinatura"),
    path("api/motoristas/proximos/", views.MotoristasProximosView.as_view(), name="proximos"),
    path("api/motoristas/activar-telegram/", views.ActivarTelegramView.as_view(), name="activar_telegram"),
    path("api/bot/update/", bot_views.BotUpdateView.as_view(), name="bot_update"),

    # Site pages
    path("motorista/cadastro/", views.CadastroMotoristaView.as_view(), name="cadastro"),
    path("motorista/login/", views.LoginMotoristaView.as_view(), name="login"),
    path("motorista/logout/", views.LogoutMotoristaView.as_view(), name="logout"),
    path("motorista/dashboard/", views.DashboardMotoristaView.as_view(), name="dashboard"),
    path("motorista/historico/", views.HistoricoMotoristaView.as_view(), name="historico"),
    path("motorista/conta/", views.ContaMotoristaView.as_view(), name="conta"),
    path("motorista/assinatura/", views.AssinaturaMotoristaView.as_view(), name="assinatura"),
    path("motorista/gerar-link-telegram/", views.GerarLinkTelegramView.as_view(), name="gerar_link_telegram"),
    path("api/motoristas/toggle-online/", views.ToggleOnlineView.as_view(), name="toggle_online"),
]
