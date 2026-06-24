"""Testes dos handlers de corridas — chamada directa."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from aiogram.types import CallbackQuery, Message
from handlers.corridas import (
    aceitar_corrida, recusar_corrida, ofertar_corrida, concluir_corrida_callback,
    receber_localizacao_aceite,
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


def _make_msg(user_id=123456789, text="ok"):
    msg = MagicMock(spec=Message)
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.chat = MagicMock()
    msg.chat.id = user_id
    msg.text = text
    msg.answer = AsyncMock()
    msg.location = MagicMock()
    msg.location.latitude = -3.1
    msg.location.longitude = -60.0
    return msg


@pytest.mark.asyncio
async def test_aceitar_corrida():
    cb = _make_cb("aceitar:42:12.00")
    state = AsyncMock()

    with patch("handlers.corridas.services.aceitar_corrida") as mock_aceitar:
        mock_aceitar.return_value = {"ok": True}
        await aceitar_corrida(cb, state)

    cb.answer.assert_called()


@pytest.mark.asyncio
async def test_aceitar_corrida_localizacao_desatualizada():
    """Se localização >30min, pede GPS antes de aceitar."""
    cb = _make_cb("aceitar:42:12.00")
    state = AsyncMock()

    with patch("handlers.corridas.services.verificar_assinatura") as mock_ver:
        mock_ver.return_value = {
            "active": True,
            "localizacao_desatualizada": True,
        }
        with patch("handlers.corridas.services.aceitar_corrida") as mock_aceitar:
            await aceitar_corrida(cb, state)

    state.set_state.assert_called()
    mock_aceitar.assert_not_called()


@pytest.mark.asyncio
async def test_aceitar_corrida_localizacao_fresca():
    """Se localização é fresca, aceita directamente."""
    cb = _make_cb("aceitar:42:12.00")
    state = AsyncMock()

    with patch("handlers.corridas.services.verificar_assinatura") as mock_ver:
        mock_ver.return_value = {
            "active": True,
            "localizacao_desatualizada": False,
        }
        with patch("handlers.corridas.services.aceitar_corrida") as mock_aceitar:
            mock_aceitar.return_value = {"ok": True}
            await aceitar_corrida(cb, state)

    mock_aceitar.assert_called_once()
    cb.answer.assert_called()


@pytest.mark.asyncio
async def test_receber_localizacao_aceite():
    """Handler de location após pedido de GPS no fluxo de aceitar."""
    msg = _make_msg()
    state = AsyncMock()
    state.get_data.return_value = {"aceitar_corrida_id": 42, "aceitar_valor": 12.0}

    with patch("handlers.corridas.services.atualizar_localizacao") as mock_loc:
        mock_loc.return_value = {"ok": True}
        with patch("handlers.corridas.services.aceitar_corrida") as mock_aceitar:
            mock_aceitar.return_value = {"ok": True}
            await receber_localizacao_aceite(msg, state)

    mock_loc.assert_called_once_with(
        telegram_id=123456789, latitude=-3.1, longitude=-60.0
    )
    mock_aceitar.assert_called_once_with(
        corrida_id=42, motorista_telegram_id=123456789
    )


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
