from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main import main_menu
from database.repository import UserRepository

router = Router(name="start")


@router.message(Command("start", "menu"))
async def start(message: Message, state: FSMContext, repo: UserRepository) -> None:
    await state.clear()
    await repo.get_or_create(message.from_user.id)
    await message.answer("Selamat datang! Atur kertas dan gaya tulisan, lalu mulai menulis.", reply_markup=main_menu())


@router.callback_query(F.data == "menu:main")
async def menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Menu utama:", reply_markup=main_menu())
    await callback.answer()


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Proses dibatalkan.", reply_markup=main_menu())


@router.message(Command("reset"))
async def reset(message: Message, state: FSMContext, repo: UserRepository) -> None:
    await state.clear()
    await repo.reset(message.from_user.id)
    await message.answer("Semua pengaturan dikembalikan ke default.", reply_markup=main_menu())


@router.callback_query(F.data == "menu:settings")
async def settings_summary(callback: CallbackQuery, repo: UserRepository) -> None:
    pref = await repo.get_or_create(callback.from_user.id)
    if pref.show_identity and (pref.identity or pref.name):
        identity = ", ".join(f"{item['label']}: {item['value']}" for item in (pref.identity or [])[:3]) or (pref.name or "tersedia")
    else:
        identity = "disembunyikan"
    date = pref.custom_date if pref.date_mode == "custom" else ("hari ini" if pref.show_date else "disembunyikan")
    await callback.message.answer(
        "Pengaturan saat ini:\n"
        f"• Buku: {pref.book_style}\n• Tulisan: {pref.handwriting_style}\n"
        f"• Tinta: {pref.ink_color}\n• Identitas: {identity}\n• Tanggal: {date}",
        reply_markup=main_menu(),
    )
    await callback.answer()
