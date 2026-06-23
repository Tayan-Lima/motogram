from django.urls import path
from . import views

app_name = "corridas"

urlpatterns = [
    path("api/corridas/", views.CriarCorridaView.as_view(), name="criar"),
    path("api/corridas/web/", views.CriarCorridaWebView.as_view(), name="criar_web"),
    path("api/corridas/<int:corrida_id>/aceitar/", views.AceitarCorridaView.as_view(), name="aceitar"),
    path("api/corridas/<int:corrida_id>/ofertar/", views.CriarOfertaView.as_view(), name="ofertar"),
    path("api/corridas/<int:corrida_id>/recusar/", views.RecusarCorridaView.as_view(), name="recusar"),
    path("api/corridas/<int:corrida_id>/concluir/", views.ConcluirCorridaView.as_view(), name="concluir"),
    path("api/corridas/<int:corrida_id>/status/", views.CorridaStatusView.as_view(), name="status"),
    path("api/corridas/<int:corrida_id>/ofertas/", views.ListarOfertasView.as_view(), name="ofertas"),
    path("api/corridas/<int:corrida_id>/escolher/", views.EscolherMotoristaView.as_view(), name="escolher"),
    path("api/corridas/<int:corrida_id>/iniciar/", views.IniciarCorridaView.as_view(), name="iniciar"),
    path("api/corridas/<int:corrida_id>/cancelar-motorista/", views.CancelarCorridaMotoristaView.as_view(), name="cancelar_motorista"),
    path("api/corridas/<int:corrida_id>/cancelar/", views.CancelarCorridaView.as_view(), name="cancelar"),
    path("api/corridas/<int:corrida_id>/avaliar/", views.AvaliarMotoristaView.as_view(), name="avaliar"),
    path("api/corridas/<int:corrida_id>/avaliar-passageiro/", views.AvaliarPassageiroView.as_view(), name="avaliar_passageiro"),
]
