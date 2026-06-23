"""Testes dos handlers do motorista — chamada directa."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from aiogram.types import Message
from handlers.motorista import ficar_online, ficar_offline, meu_status, ganhos, minha_conta


def _make_msg(text):
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.from_user = MagicMock()
    msg.from_user.id = 123456789
    msg.chat = MagicMock()
    msg.chat.id = 123456789
    msg.answer = AsyncMock()
    msg.reply = AsyncMock()
    return msg


@pytest.mark.asyncio
async def test_ficar_online_assinatura_activa():
    msg = _make_msg("🟢 Ficar Online")
    state = AsyncMock()

    with patch("handlers.motorista.services.verificar_assinatura") as mock_ver:
        mock_ver.return_value = {"active": True}
        await ficar_online(msg, state)

    msg.answer.assert_called()
    texto = msg.answer.call_args[0][0] if msg.answer.call_args[0] else msg.answer.call_args[1].get("text", "")
    assert "online" in texto.lower()


@pytest.mark.asyncio
async def test_ficar_online_sem_assinatura():
    msg = _make_msg("🟢 Ficar Online")
    state = AsyncMock()

    with patch("handlers.motorista.services.verificar_assinatura") as mock_ver:
        mock_ver.return_value = {"active": False, "message": "Expirada"}
        await ficar_online(msg, state)

    msg.answer.assert_called()
    texto = msg.answer.call_args[0][0] if msg.answer.call_args[0] else msg.answer.call_args[1].get("text", "")
    assert "assinatura" in texto.lower()


@pytest.mark.asyncio
async def test_ficar_offline():
    msg = _make_msg("🔴 Ficar Offline")
    state = AsyncMock()

    await ficar_offline(msg, state)

    msg.answer.assert_called()
    texto = msg.answer.call_args[0][0] if msg.answer.call_args[0] else msg.answer.call_args[1].get("text", "")
    assert "offline" in texto.lower()


@pytest.mark.asyncio
async def test_meu_status():
    msg = _make_msg("📊 Meu Status")

    with patch("handlers.motorista.services.verificar_assinatura") as mock_ver:
        mock_ver.return_value = {"active": True}
        await meu_status(msg)

    msg.answer.assert_called()


@pytest.mark.asyncio
async def test_ganhos():
    msg = _make_msg("📋 Ganhos")
    await ganhos(msg)

    msg.answer.assert_called()


@pytest.mark.asyncio
async def test_minha_conta():
    msg = _make_msg("🏍️ Minha Conta")
    await minha_conta(msg)

    msg.answer.assert_called()
