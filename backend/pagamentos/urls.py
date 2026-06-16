from django.urls import path
from . import views

app_name = "pagamentos"

urlpatterns = [
    path("api/assinaturas/criar/", views.CriarAssinaturaView.as_view(), name="criar_assinatura"),
    path("api/webhook/mercadopago/", views.WebhookMercadoPagoView.as_view(), name="webhook_mercadopago"),
]
