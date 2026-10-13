from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.handlers import admin, book, date, generate, handwriting, identity, ink, start
from config.settings import Settings
from database.db import Database
from database.repository import UserRepository
from services.generation_service import GenerationService


async def main() -> None:
    settings = Settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN belum diatur. Salin .env.example menjadi .env lalu isi token bot.")
    settings.prepare()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    database = Database(settings.database_path)
    await database.initialize()
    repo = UserRepository(database)
    generator = GenerationService(settings.assets_dir, settings.max_text_length)
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_routers(admin.router, start.router, book.router, handwriting.router, identity.router, date.router, ink.router, generate.router)
    dp["repo"] = repo
    dp["generator"] = generator
    dp["settings"] = settings
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
