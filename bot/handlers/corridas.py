"""Handlers de corridas — aceitar, ofertar, recusar, concluir."""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

import messages
import services
from states import MotoristaStates

router = Router()


@router.callback_query(F.data.startswith("aceitar:"))
async def aceitar_corrida(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    try:
        corrida_id = int(parts[1])
        valor = float(parts[2]) if len(parts) > 2 else 0.0
    except (ValueError, IndexError):
        await callback.answer("Dados inválidos.", show_alert=True)
        return

    resultado = services.aceitar_corrida(
        corrida_id=corrida_id,
        motorista_telegram_id=callback.from_user.id,
    )

    if "erro" in resultado:
        await callback.answer(resultado["erro"], show_alert=True)
        return

    await callback.message.edit_text(
        f"✅ *Oferta enviada!*\n\nAguardando o passageiro escolher...\n\n💰 R$ {valor:.2f}",
        parse_mode="Markdown",
    )
    await state.set_state(MotoristaStates.aguardando_oferta)
    await callback.answer("Oferta enviada!")


@router.callback_query(F.data.startswith("recusar:"))
async def recusar_corrida(callback: CallbackQuery):
    parts = callback.data.split(":")
    try:
        corrida_id = int(parts[1])
    except (ValueError, IndexError):
        await callback.answer("Dados inválidos.", show_alert=True)
        return

    resultado = services.recusar_corrida(
        corrida_id=corrida_id,
        motorista_telegram_id=callback.from_user.id,
    )

    if "erro" in resultado:
        await callback.answer(resultado["erro"], show_alert=True)
        return

    await callback.message.edit_text(messages.OFERTA_RECUSADA, parse_mode="Markdown")
    await callback.answer("Recusada.")


@router.callback_query(F.data.startswith("ofertar:"))
async def ofertar_corrida(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    try:
        corrida_id = int(parts[1])
    except (ValueError, IndexError):
        await callback.answer("Dados inválidos.", show_alert=True)
        return

    await state.update_data(ofertar_corrida_id=corrida_id)
    await state.set_state(MotoristaStates.contra_oferta)
    await callback.message.answer(
        messages.DIGITE_OFERTA,
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(MotoristaStates.contra_oferta)
async def receber_contra_oferta(message: Message, state: FSMContext):
    try:
        valor = float(message.text.replace(",", "."))
        if valor <= 0:
            raise ValueError()
    except ValueError:
        await message.answer(messages.VALOR_INVALIDO, parse_mode="Markdown")
        return

    data = await state.get_data()
    corrida_id = data.get("ofertar_corrida_id")
    if not corrida_id:
        await message.answer(messages.ERRO_GENERICO, parse_mode="Markdown")
        await state.set_state(MotoristaStates.menu_principal)
        return

    resultado = services.ofertar_corrida(
        corrida_id=corrida_id,
        motorista_telegram_id=message.from_user.id,
        valor=valor,
    )

    if "erro" in resultado:
        await message.answer(resultado["erro"], parse_mode="Markdown")
        await state.set_state(MotoristaStates.menu_principal)
        return

    await message.answer(
        messages.OFERTA_ENVIADA.format(valor=valor),
        parse_mode="Markdown",
    )
    await state.set_state(MotoristaStates.aguardando_oferta)


@router.callback_query(F.data.startswith("concluir:"))
async def concluir_corrida_callback(callback: CallbackQuery):
    parts = callback.data.split(":")
    try:
        corrida_id = int(parts[1])
    except (ValueError, IndexError):
        await callback.answer("Dados inválidos.", show_alert=True)
        return

    resultado = services.concluir_corrida(
        corrida_id=corrida_id,
        motorista_telegram_id=callback.from_user.id,
    )

    if "erro" in resultado:
        await callback.answer(resultado["erro"], show_alert=True)
        return

    valor = resultado.get("valor", "0.00")
    distancia = resultado.get("distancia_km", "0")
    await callback.message.edit_text(
        messages.CORRIDA_CONCLUIDA.format(valor=valor, distancia=distancia),
        parse_mode="Markdown",
    )
    await callback.answer("Concluída!")


@router.callback_query(F.data.startswith("nao_escolhido:"))
async def nao_escolhido(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        messages.CORRIDA_NAO_ESCOLHIDA,
        parse_mode="Markdown",
    )
    await state.set_state(MotoristaStates.disponivel)


@router.callback_query(F.data.startswith("expirado:"))
async def corrida_expirada(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        messages.CORRIDA_EXPIRADA,
        parse_mode="Markdown",
    )
    await state.set_state(MotoristaStates.disponivel)


@router.message(F.text == "✅ Concluir corrida")
async def concluir_por_botao(message: Message, state: FSMContext):
    data = await state.get_data()
    corrida_id = data.get("corrida_id_ativa")
    if not corrida_id:
        await message.answer("Nenhuma corrida activa encontrada.")
        return

    resultado = services.concluir_corrida(
        corrida_id=corrida_id,
        motorista_telegram_id=message.from_user.id,
    )

    if "erro" in resultado:
        await message.answer(resultado["erro"])
        return

    valor = resultado.get("valor", "0.00")
    distancia = resultado.get("distancia_km", "0")
    await message.answer(
        messages.CORRIDA_CONCLUIDA.format(valor=valor, distancia=distancia),
        parse_mode="Markdown",
    )
    await state.set_state(MotoristaStates.disponivel)
