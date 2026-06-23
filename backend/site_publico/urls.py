from django.urls import path
from . import views

app_name = "site_publico"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("passageiro/", views.pedir_corrida, name="pedir_corrida"),
    path("passageiro/cadastro/", views.CadastroPassageiroView.as_view(), name="cadastro"),
    path("passageiro/login/", views.LoginPassageiroView.as_view(), name="login"),
    path("passageiro/recuperar-senha/", views.RecuperarSenhaPassageiroView.as_view(), name="recuperar_senha"),
    path("passageiro/logout/", views.LogoutPassageiroView.as_view(), name="logout"),
    path("passageiro/perfil/", views.PerfilPassageiroView.as_view(), name="perfil"),
    path("passageiro/confirmacao/<int:corrida_id>/", views.confirmacao, name="confirmacao"),
    path("passageiro/acompanhar/<int:corrida_id>/", views.acompanhar, name="acompanhar"),
    path("passageiro/upload-foto/", views.UploadFotoPassageiroView.as_view(), name="upload_foto"),
    path("passageiro/confirmar-email/<str:token>/", views.ConfirmarEmailView.as_view(), name="confirmar_email"),
    path("api/passageiros/favoritos/", views.ListarFavoritosView.as_view(), name="listar_favoritos"),
    path("api/passageiros/favoritos/criar/", views.CriarFavoritoView.as_view(), name="criar_favorito"),
    path("api/passageiros/favoritos/<int:favorito_id>/remover/", views.RemoverFavoritoView.as_view(), name="remover_favorito"),
]
