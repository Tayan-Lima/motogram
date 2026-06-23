"""Testes dos handlers de corridas — chamada directa."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from aiogram.types import CallbackQuery, Message
from handlers.corridas import (
    aceitar_corrida, recusar_corrida, ofertar_corrida, concluir_corrida_callback,
)


def _make_cb(data, user_id=123456789):
    cb = MagicMock(spec=CallbackQuery)
    cb.data = data
    cb.from_user = MagicMock()
    cb.from_user.id = user_id
    msg = MagicMock(spec=Message)
    msg.chat = MagicMock()
    msg.chat.id = user_id
    msg.text = "inline message"
    msg.answer = AsyncMock()
    msg.edit_text = AsyncMock()
    msg.edit_reply_markup = AsyncMock()
    cb.message = msg
    cb.answer = AsyncMock()
    return cb


@pytest.mark.asyncio
async def test_aceitar_corrida():
    cb = _make_cb("aceitar:42:12.00")
    state = AsyncMock()

    with patch("handlers.corridas.services.aceitar_corrida") as mock_aceitar:
        mock_aceitar.return_value = {"ok": True}
        await aceitar_corrida(cb, state)

    cb.answer.assert_called()


@pytest.mark.asyncio
async def test_recusar_corrida():
    cb = _make_cb("recusar:42")

    with patch("handlers.corridas.services.recusar_corrida") as mock_recusar:
        mock_recusar.return_value = {"ok": True}
        await recusar_corrida(cb)

    cb.answer.assert_called()


@pytest.mark.asyncio
async def test_ofertar_corrida():
    cb = _make_cb("ofertar:42")
    state = AsyncMock()

    with patch("handlers.corridas.services.ofertar_corrida") as mock_ofertar:
        mock_ofertar.return_value = {"ok": True}
        await ofertar_corrida(cb, state)

    cb.answer.assert_called()


@pytest.mark.asyncio
async def test_concluir_corrida():
    cb = _make_cb("concluir:42")
    state = AsyncMock()

    with patch("handlers.corridas.services.concluir_corrida") as mock_concluir:
        mock_concluir.return_value = {"ok": True}
        await concluir_corrida_callback(cb, state)

    cb.answer.assert_called()
