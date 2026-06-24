"""Testes dos handlers do motorista — chamada directa."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from aiogram.types import Message
from handlers.motorista import (
    ficar_online, ficar_offline, meu_status, ganhos, minha_conta, receber_localizacao_live,
)


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


def _make_msg_location():
    msg = MagicMock(spec=Message)
    msg.from_user = MagicMock()
    msg.from_user.id = 123456789
    msg.chat = MagicMock()
    msg.chat.id = 123456789
    msg.answer = AsyncMock()
    msg.location = MagicMock()
    msg.location.latitude = -3.1
    msg.location.longitude = -60.0
    return msg


@pytest.mark.asyncio
async def test_ficar_online_assinatura_activa():
    msg = _make_msg("🟢 Ficar Online")
    state = AsyncMock()

    with patch("handlers.motorista.services.verificar_assinatura") as mock_ver:
        mock_ver.return_value = {"active": True}
        with patch("handlers.motorista.services.toggle_online") as mock_toggle:
            mock_toggle.return_value = {"ok": True}
            await ficar_online(msg, state)

    mock_toggle.assert_called_once_with(123456789, True)
    assert msg.answer.call_count >= 2  # FICAR_ONLINE + INSTRUCAO_LIVE_LOCATION


@pytest.mark.asyncio
async def test_ficar_online_sem_assinatura():
    msg = _make_msg("🟢 Ficar Online")
    state = AsyncMock()

    with patch("handlers.motorista.services.verificar_assinatura") as mock_ver:
        mock_ver.return_value = {"active": False, "message": "Expirada"}
        with patch("handlers.motorista.services.toggle_online") as mock_toggle:
            await ficar_online(msg, state)

    mock_toggle.assert_not_called()
    msg.answer.assert_called()


@pytest.mark.asyncio
async def test_ficar_offline():
    msg = _make_msg("🔴 Ficar Offline")
    state = AsyncMock()

    with patch("handlers.motorista.services.toggle_online") as mock_toggle:
        mock_toggle.return_value = {"ok": True}
        await ficar_offline(msg, state)

    mock_toggle.assert_called_once_with(123456789, False)
    msg.answer.assert_called()


@pytest.mark.asyncio
async def test_receber_localizacao_live():
    msg = _make_msg_location()

    with patch("handlers.motorista.services.verificar_assinatura") as mock_ver:
        mock_ver.return_value = {"active": True}
        with patch("handlers.motorista.services.atualizar_localizacao") as mock_loc:
            await receber_localizacao_live(msg)

    mock_loc.assert_called_once_with(
        telegram_id=123456789, latitude=-3.1, longitude=-60.0
    )


@pytest.mark.asyncio
async def test_receber_localizacao_live_nao_motorista():
    msg = _make_msg_location()

    with patch("handlers.motorista.services.verificar_assinatura") as mock_ver:
        mock_ver.return_value = {"active": False}
        with patch("handlers.motorista.services.atualizar_localizacao") as mock_loc:
            await receber_localizacao_live(msg)

    mock_loc.assert_not_called()


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
