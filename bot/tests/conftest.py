"""Fixtures para testes do bot Telegram."""

import os
import sys
from pathlib import Path

bot_dir = Path(__file__).resolve().parent.parent
if str(bot_dir) not in sys.path:
    sys.path.insert(0, str(bot_dir))

os.environ.setdefault("BOT_SECRET", "test-bot-secret")
os.environ.setdefault("BACKEND_URL", "http://localhost:8000")
os.environ.setdefault("SITE_URL", "http://test.local")
os.environ.setdefault("TELEGRAM_TOKEN", "test_token")


import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from aiogram.types import (
    Message, Chat, User, CallbackQuery, MessageEntity,
)
from aiogram.fsm.context import FSMContext
