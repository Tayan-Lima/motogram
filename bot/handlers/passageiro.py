"""Handlers do fluxo do passageiro."""

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

import messages
import services
from states import PassageiroStates

router = Router()


@router.message(F.text == "📍 Pedir corrida")
async def pedir_corrida(message: Message, state: FSMContext):
    """Inicia o fluxo de pedido de corrida."""
    await state.set_state(PassageiroStates.aguardando_localizacao)
    await message.answer(
        messages.PASSAGEIRO_LOCALIZACAO,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(PassageiroStates.aguardando_localizacao, F.location)
async def receber_localizacao(message: Message, state: FSMContext):
    """Recebe a localização do passageiro e cria a corrida."""
    lat = message.location.latitude
    lon = message.location.longitude

    await state.update_data(origem_lat=lat, origem_lon=lon)
    await state.set_state(PassageiroStates.aguardando_destino)

    await message.answer(
        messages.PASSAGEIRO_DESTINO,
        parse_mode="Markdown",
    )


@router.message(PassageiroStates.aguardando_destino, F.location)
async def receber_destino(message: Message, state: FSMContext):
    """Recebe o destino (opcional) e cria a corrida."""
    data = await state.get_data()
    lat = data["origem_lat"]
    lon = data["origem_lon"]

    resultado = services.criar_corrida(
        passageiro_telegram_id=message.from_user.id,
        lat=lat,
        lon=lon,
        destino_lat=message.location.latitude,
        destino_lon=message.location.longitude,
    )

    if "erro" in resultado:
        await message.answer(messages.ERRO_GENERICO)
        await state.clear()
        return

    await state.set_state(PassageiroStates.aguardando_motorista)
    await state.update_data(corrida_id=resultado.get("id"))

    await message.answer(
        messages.PASSAGEIRO_CORRIDA_CRIADA,
        parse_mode="Markdown",
    )


@router.message(PassageiroStates.aguardando_destino, F.text == "/pular")
async def pular_destino(message: Message, state: FSMContext):
    """Pula o destino e cria a corrida só com origem."""
    data = await state.get_data()
    lat = data["origem_lat"]
    lon = data["origem_lon"]

    resultado = services.criar_corrida(
        passageiro_telegram_id=message.from_user.id,
        lat=lat,
        lon=lon,
    )

    if "erro" in resultado:
        await message.answer(messages.ERRO_GENERICO)
        await state.clear()
        return

    await state.set_state(PassageiroStates.aguardando_motorista)
    await state.update_data(corrida_id=resultado.get("id"))

    await message.answer(
        messages.PASSAGEIRO_CORRIDA_CRIADA,
        parse_mode="Markdown",
    )


@router.message(F.text == "📋 Ajuda")
async def ajuda(message: Message):
    """Mostra comandos disponíveis."""
    await message.answer(messages.AJUDA, parse_mode="Markdown")
