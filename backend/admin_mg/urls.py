import os
from django.urls import path
from . import views

PREFIX = os.environ.get("ADMIN_SECRET_PATH", "admin_mg")

app_name = "admin_mg"

urlpatterns = [
    path(f"{PREFIX}/", views.AdminDashboardView.as_view(), name="dashboard"),
    path(f"{PREFIX}/entrar/", views.AdminLoginView.as_view(), name="login"),
    path(f"{PREFIX}/cadastros/", views.CadastrosPendentesView.as_view(), name="cadastros_pendentes"),
    path(f"{PREFIX}/cadastros/<int:motorista_id>/analisar/", views.AnalisarCadastroView.as_view(), name="analisar_cadastro"),
    path(f"{PREFIX}/corridas/", views.HistoricoCorridasView.as_view(), name="historico_corridas"),
    path(f"{PREFIX}/motoristas/", views.MotoristasListView.as_view(), name="motoristas"),
]
