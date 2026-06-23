import asyncio
import hashlib
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv(override=True)

from handlers import motorista, corridas, start

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
BOT_SECRET = os.environ.get("BOT_SECRET", "")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN não definido. Verifica o ficheiro .env")
if not BOT_SECRET:
    raise RuntimeError("BOT_SECRET não definido. Verifica o ficheiro .env")

_BOT_SECRET_HASH = hashlib.sha256(BOT_SECRET.encode()).hexdigest()[:8]
logging.info("Diagnóstico: BOT_SECRET hash=%s BACKEND_URL=%s", _BOT_SECRET_HASH, os.environ.get("BACKEND_URL", "n/a"))


async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(start.router)
    dp.include_router(motorista.router)
    dp.include_router(corridas.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
