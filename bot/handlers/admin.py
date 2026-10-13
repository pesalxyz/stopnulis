from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config.settings import Settings
from database.repository import UserRepository


router = Router(name="admin")


@router.message(Command("stats"))
async def stats(message: Message, repo: UserRepository, settings: Settings) -> None:
    if settings.admin_telegram_id is None or message.from_user.id != settings.admin_telegram_id:
        # Do not reveal whether the command exists or whether an account is
        # configured as admin.
        await message.answer("Perintah tidak tersedia.")
        return
    values = await repo.usage_stats()
    await message.answer(
        "Statistik StopNulis\n"
        f"• Total akun terdaftar: {values['total_users']}\n"
        f"• Akun yang pernah membuat output: {values['active_users']}\n"
        f"• Akun aktif hari ini: {values['active_today']}\n"
        f"• Total output dibuat: {values['total_generations']}"
    )
