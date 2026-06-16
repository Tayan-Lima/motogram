"""Handler /start — menu inicial do bot e comandos gerais."""

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command

import messages
import services

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Menu inicial — escolha entre passageiro e motorista."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏍️ Sou motorista")],
            [KeyboardButton(text="📍 Pedir corrida")],
            [KeyboardButton(text="📋 Ajuda")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    await message.answer(
        messages.START_ESCOLHA,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


@router.message(Command("corrida"))
async def cmd_corrida(message: Message):
    """Atalho para pedir corrida."""
    await message.answer(
        messages.PASSAGEIRO_LOCALIZACAO,
        parse_mode="Markdown",
    )


@router.message(Command("status"))
async def cmd_status(message: Message):
    """Ver estado da assinatura."""
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


@router.message(Command("ganhos"))
async def cmd_ganhos(message: Message):
    """Resumo de ganhos (placeholder)."""
    await message.answer(
        "📊 *Ganhos*\n\n"
        "O resumo completo de ganhos está disponível no site:\n"
        "motogram.app/motorista/dashboard/",
        parse_mode="Markdown",
    )


@router.message(Command("renovar"))
async def cmd_renovar(message: Message):
    """Link para renovar assinatura."""
    await message.answer(
        "🔗 Renova a tua assinatura em:\n"
        "motogram.app/motorista/conta/",
    )


@router.message(Command("ajuda"))
async def cmd_ajuda(message: Message):
    """Mostra comandos disponíveis."""
    await message.answer(messages.AJUDA, parse_mode="Markdown")
