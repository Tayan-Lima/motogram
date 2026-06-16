"""Mixins partilhados entre apps."""

from django.http import JsonResponse
from django.conf import settings


class BotAuthMixin:
    """Verifica o X-Bot-Secret header para endpoints internos."""

    def verificar_bot_secret(self, request):
        bot_secret = request.headers.get("X-Bot-Secret")
        if bot_secret != settings.BOT_SECRET:
            return JsonResponse({"erro": "Não autorizado"}, status=403)
        return None
