"""Views da app motoristas — endpoints para o bot webhook."""

import json
from django.http import JsonResponse
from django.views import View
from django.conf import settings


class BotUpdateView(View):
    """POST /api/bot/update/ — recebe updates do Telegram (webhook mode)."""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"ok": False}, status=400)

        # Em modo webhook, o aiogram precisa deste endpoint para receber updates
        # O aiogram processa o update internamente via Dispatcher
        return JsonResponse({"ok": True})
