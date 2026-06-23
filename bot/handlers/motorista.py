"""Handlers do motorista — menu, status, toggle online/offline."""

import os
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

import messages
import services
from states import MotoristaStates

router = Router()
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8000")


def _menu_principal():
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
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
            [KeyboardButton(text="🧹 Limpar Chat")],
        ],
        resize_keyboard=True,
    )


def _menu_online():
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
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
            [KeyboardButton(text="🧹 Limpar Chat")],
        ],
        resize_keyboard=True,
    )


@router.message(F.text == "🟢 Ficar Online")
async def ficar_online(message: Message, state: FSMContext):
    resultado = services.verificar_assinatura(message.from_user.id)
    if not resultado.get("active"):
        link = resultado.get("link", f"{SITE_URL}/motorista/conta/")
        await message.answer(
            messages.STATUS_INATIVO.format(link=link),
            parse_mode="Markdown",
        )
        return

    await message.answer(
        messages.FICAR_ONLINE,
        parse_mode="Markdown",
        reply_markup=_menu_online(),
    )
    await state.set_state(MotoristaStates.disponivel)


@router.message(F.text == "🔴 Ficar Offline")
async def ficar_offline(message: Message, state: FSMContext):
    await message.answer(
        messages.FICAR_OFFLINE,
        parse_mode="Markdown",
        reply_markup=_menu_principal(),
    )
    await state.set_state(MotoristaStates.menu_principal)


@router.message(F.text == "📊 Meu Status")
async def meu_status(message: Message):
    resultado = services.verificar_assinatura(message.from_user.id)
    if resultado.get("active"):
        await message.answer(
            messages.STATUS_ATIVO.format(data=resultado.get("valida_ate", "N/A")),
            parse_mode="Markdown",
        )
    else:
        link = resultado.get("link", f"{SITE_URL}/motorista/conta/")
        await message.answer(
            messages.STATUS_INATIVO.format(link=link),
            parse_mode="Markdown",
        )


@router.message(F.text == "📋 Ganhos")
async def ganhos(message: Message):
    await message.answer(
        f"📊 *Ganhos*\n\nO resumo completo está no site:\n{SITE_URL}/motorista/dashboard/",
        parse_mode="Markdown",
    )


@router.message(F.text == "🏍️ Minha Conta")
async def minha_conta(message: Message):
    await message.answer(
        f"🏍️ *Minha Conta*\n\nGere o seu token, veja assinatura e mais:\n{SITE_URL}/motorista/conta/",
        parse_mode="Markdown",
    )


@router.message(Command("status"))
async def cmd_status(message: Message):
    await meu_status(message)


@router.message(Command("ganhos"))
async def cmd_ganhos(message: Message):
    await ganhos(message)


@router.message(F.text == "🧹 Limpar Chat")
async def limpar_chat(message: Message):
    resultado = services.limpar_mensagens(message.from_user.id)
    if "erro" in resultado:
        await message.answer(resultado["erro"])
        return
    n = resultado.get("apagadas", 0)
    await message.answer(
        messages.CHAT_LIMPO.format(n=n),
        parse_mode="Markdown",
    )
