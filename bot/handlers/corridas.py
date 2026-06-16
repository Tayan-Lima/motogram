"""Handlers de corridas — aceitar, recusar, concluir."""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

import messages
import services

router = Router()


@router.callback_query(F.data.startswith("aceitar:"))
async def aceitar_corrida(callback: CallbackQuery):
    """Motorista aceita uma corrida."""
    try:
        corrida_id = int(callback.data.split(":")[1])
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

    passageiro = resultado.get("passageiro", {})
    origem = resultado.get("origem", "localização do passageiro")
    telefone = passageiro.get("telefone", "N/A")

    await callback.message.edit_text(
        messages.MOTORISTA_CORRIDA_ACEITA.format(
            origem=origem,
            telefone=telefone,
        ),
        parse_mode="Markdown",
    )
    await callback.answer("✅ Corrida aceite!")


@router.callback_query(F.data.startswith("recusar:"))
async def recusar_corrida(callback: CallbackQuery):
    """Motorista recusa uma corrida."""
    try:
        corrida_id = int(callback.data.split(":")[1])
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

    await callback.message.edit_text(messages.MOTORISTA_CORRIDA_RECUSADA)
    await callback.answer("❌ Corrida recusada.")


@router.message(F.text.startswith("/concluir"))
async def concluir_corrida(message: Message):
    """Motorista conclui uma corrida activa."""
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Uso: /concluir <id_da_corrida>")
        return

    try:
        corrida_id = int(parts[1])
    except ValueError:
        await message.answer("ID de corrida inválido. Use: /concluir <número>")
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
