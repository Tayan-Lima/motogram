from django.urls import path
from . import views

app_name = "admin_mg"

urlpatterns = [
    path("admin_mg/", views.AdminDashboardView.as_view(), name="dashboard"),
    path("admin_mg/cadastros/", views.CadastrosPendentesView.as_view(), name="cadastros_pendentes"),
    path("admin_mg/cadastros/<int:motorista_id>/analisar/", views.AnalisarCadastroView.as_view(), name="analisar_cadastro"),
    path("admin_mg/corridas/", views.HistoricoCorridasView.as_view(), name="historico_corridas"),
    path("admin_mg/motoristas/", views.MotoristasListView.as_view(), name="motoristas"),
]
