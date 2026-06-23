"""Testes do handler /start — chamada directa dos handlers."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from aiogram.types import Message, MessageEntity
from handlers.start import cmd_start_token, cmd_start, cmd_ajuda


def _make_msg(text, user_id=123456789):
    entities = None
    if text.startswith("/start") or text.startswith("/ajuda"):
        cmd_end = text.find(" ") if " " in text else len(text)
        entities = [MessageEntity(type="bot_command", offset=0, length=cmd_end)]
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.chat = MagicMock()
    msg.chat.id = user_id
    msg.entities = entities
    msg.answer = AsyncMock()
    msg.reply = AsyncMock()
    return msg


def _make_command():
    cmd = MagicMock()
    cmd.args = None
    return cmd


@pytest.mark.asyncio
async def test_start_plain_motorista_inactivo():
    msg = _make_msg("/start")
    state = AsyncMock()

    with patch("handlers.start.services.verificar_assinatura") as mock_ver:
        mock_ver.return_value = {"active": False, "message": "Assinatura inativa"}
        await cmd_start(msg, state)

    msg.answer.assert_called_once()
    texto = msg.answer.call_args[0][0] if msg.answer.call_args[0] else msg.answer.call_args[1].get("text", "")
    assert "Bem-vindo" in texto or "token" in texto.lower() or "ativ" in texto.lower()


@pytest.mark.asyncio
async def test_start_plain_motorista_activo():
    msg = _make_msg("/start")
    state = AsyncMock()

    with patch("handlers.start.services.verificar_assinatura") as mock_ver:
        mock_ver.return_value = {"active": True}
        await cmd_start(msg, state)

    msg.answer.assert_called_once()
    texto = msg.answer.call_args[0][0] if msg.answer.call_args[0] else msg.answer.call_args[1].get("text", "")
    assert "Olá" in texto
    assert "reply_markup" in msg.answer.call_args[1]


@pytest.mark.asyncio
async def test_start_com_token_valido():
    msg = _make_msg("/start TOKEN123")
    cmd = _make_command()
    cmd.args = "TOKEN123"
    state = AsyncMock()

    with patch("handlers.start.services.activar_telegram") as mock_act:
        mock_act.return_value = {"ok": True}
        await cmd_start_token(msg, cmd, state)

    msg.answer.assert_called_once()
    texto = msg.answer.call_args[0][0] if msg.answer.call_args[0] else msg.answer.call_args[1].get("text", "")
    assert "Olá" in texto


@pytest.mark.asyncio
async def test_start_com_token_invalido():
    msg = _make_msg("/start TOKEN_INVALIDO")
    cmd = _make_command()
    cmd.args = "TOKEN_INVALIDO"
    state = AsyncMock()

    with patch("handlers.start.services.activar_telegram") as mock_act:
        mock_act.return_value = {"erro": "Token inválido"}
        await cmd_start_token(msg, cmd, state)

    msg.answer.assert_called_once()
    texto = msg.answer.call_args[0][0] if msg.answer.call_args[0] else msg.answer.call_args[1].get("text", "")
    assert "inválido" in texto.lower()


@pytest.mark.asyncio
async def test_ajuda_handler():
    msg = _make_msg("/ajuda")
    await cmd_ajuda(msg)

    msg.answer.assert_called_once()
