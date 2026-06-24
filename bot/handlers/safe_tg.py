"""Wrappers seguros para chamadas à API Telegram com try/except.

Em rede 3G intermitente, chamadas à API Telegram podem falhar
com TelegramNetworkError, TelegramRetryAfter, etc.
Estes wrappers evitam que o handler inteiro caia.
"""

import logging

logger = logging.getLogger(__name__)


async def safe_edit_text(message, text, **kwargs):
    try:
        return await message.edit_text(text, **kwargs)
    except Exception as e:
        logger.debug("safe_edit_text: %s", e)


async def safe_answer(message, text=None, **kwargs):
    try:
        if text is not None:
            return await message.answer(text, **kwargs)
        else:
            return await message.answer(**kwargs) if hasattr(message, 'show_alert') else None
    except Exception as e:
        logger.debug("safe_answer: %s", e)


async def safe_answer_callback(callback, text=None, **kwargs):
    try:
        return await callback.answer(text=text, **kwargs)
    except Exception as e:
        logger.debug("safe_answer_callback: %s", e)


async def safe_send_message(bot_or_message, chat_id, text, **kwargs):
    try:
        return await bot_or_message.answer(text, **kwargs)
    except Exception as e:
        logger.debug("safe_send_message: %s", e)
