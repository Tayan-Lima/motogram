"""Handlers do fluxo do motorista."""

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

import messages
import services
from states import MotoristaStates

router = Router()


@router.message(F.text == "🏍️ Sou motorista")
async def sou_motorista(message: Message):
    """Verifica estado do motorista."""
    resultado = services.verificar_assinatura(message.from_user.id)

    if resultado.get("active"):
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🟢 Ficar disponível")],
                [KeyboardButton(text="📊 Meu status")],
                [KeyboardButton(text="📋 Ajuda")],
            ],
            resize_keyboard=True,
        )
        await message.answer(
            messages.MOTORISTA_STATUS_ATIVO.format(data="activa"),
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    else:
        link = resultado.get("link", "motogram.app/motorista/conta")
        await message.answer(
            messages.MOTORISTA_STATUS_INATIVO.format(link=link),
            parse_mode="Markdown",
        )


@router.message(F.text == "📊 Meu status")
async def meu_status(message: Message):
    """Mostra status da assinatura do motorista."""
    resultado = services.verificar_assinatura(message.from_user.id)

    if resultado.get("active"):
        await message.answer(
            messages.MOTORISTA_STATUS_ATIVO_SIMPLES,
            parse_mode="Markdown",
        )
    else:
        link = resultado.get("link", "motogram.app/motorista/conta")
        await message.answer(
            messages.MOTORISTA_STATUS_INATIVO_SIMPLES.format(link=link),
        )


@router.message(F.text == "🟢 Ficar disponível")
async def ficar_disponivel(message: Message):
    """Motorista fica disponível para receber corridas."""
    resultado = services.verificar_assinatura(message.from_user.id)

    if not resultado.get("active"):
        link = resultado.get("link", "motogram.app/motorista/conta")
        await message.answer(
            messages.MOTORISTA_STATUS_INATIVO.format(link=link),
            parse_mode="Markdown",
        )
        return

    await message.answer(
        messages.MOTORISTA_DISPONIVEL,
        parse_mode="Markdown",
    )
