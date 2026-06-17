"""Handler /start — guardião de token e menu principal do motorista."""

import os
from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
import messages
import services
from states import MotoristaStates

router = Router()
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8000")


def _menu_principal_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟢 Ficar Online")],
            [
                KeyboardButton(text="📊 Meu Status"),
                KeyboardButton(text="📋 Ganhos"),
            ],
            [
                KeyboardButton(text="🏍️ Minha Conta"),
                KeyboardButton(text="❓ Ajuda"),
            ],
        ],
        resize_keyboard=True,
    )


def _menu_online_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔴 Ficar Offline")],
            [
                KeyboardButton(text="📊 Meu Status"),
                KeyboardButton(text="📋 Ganhos"),
            ],
            [
                KeyboardButton(text="🏍️ Minha Conta"),
                KeyboardButton(text="❓ Ajuda"),
            ],
        ],
        resize_keyboard=True,
    )


@router.message(CommandStart(deep_link=True))
async def cmd_start_token(message: Message, command: CommandStart, state: FSMContext):
    """Valida token enviado via deep link."""
    token = command.args
    telegram_id = message.from_user.id

    resultado = services.activar_telegram(token=token, telegram_id=telegram_id)

    if resultado.get("ok"):
        nome = resultado.get("motorista", "Motorista")
        await message.answer(
            messages.MENU_PRINCIPAL.format(nome=nome),
            parse_mode="Markdown",
            reply_markup=_menu_principal_keyboard(),
        )
        await state.set_state(MotoristaStates.menu_principal)
        return

    await message.answer(
        messages.TOKEN_INVALIDO.format(link=f"{SITE_URL}/motorista/conta/"),
        parse_mode="Markdown",
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Sem token — barra entrada de estranhos."""
    telegram_id = message.from_user.id
    resultado = services.verificar_assinatura(telegram_id)

    if resultado.get("active"):
        nome = resultado.get("nome", "Motorista")
        await message.answer(
            messages.MENU_PRINCIPAL.format(nome=nome),
            parse_mode="Markdown",
            reply_markup=_menu_principal_keyboard(),
        )
        await state.set_state(MotoristaStates.menu_principal)
        return

    await message.answer(
        messages.BOAS_VINDAS.format(link=f"{SITE_URL}/motorista/conta/"),
        parse_mode="Markdown",
    )


@router.message(Command("ajuda"))
async def cmd_ajuda(message: Message):
    await message.answer(messages.AJUDA, parse_mode="Markdown")
