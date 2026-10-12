from __future__ import annotations

import asyncio
from io import BytesIO

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from PIL import Image, UnidentifiedImageError

from bot.keyboards.books import book_preview_menu, books_menu
from bot.keyboards.main import main_menu
from bot.states.states import BotStates
from config.settings import Settings
from database.repository import UserRepository
from config.books import book_registry
from renderer.paper import load_paper

router = Router(name="book")


@router.callback_query(F.data == "menu:book")
async def choose_book(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BotStates.SETTING_BOOK)
    await callback.message.answer("Pilih template buku:", reply_markup=books_menu())
    await callback.answer()


@router.callback_query(BotStates.SETTING_BOOK, F.data.regexp(r"^book:book_[0-9]+$"))
async def preview_builtin_book(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    template_id = callback.data.split(":", 1)[1]
    registry = book_registry(settings.assets_dir.parent / "menu_buku")
    template = registry.get(template_id)
    if template is None:
        await callback.answer("Template tidak ditemukan.", show_alert=True)
        return
    image, _ = load_paper(template_id, settings.assets_dir / "papers", settings.assets_dir.parent / "menu_buku")
    buffer = BytesIO()
    preview = image.convert("RGB")
    preview.thumbnail((900, 1273), Image.Resampling.LANCZOS)
    preview.save(buffer, "JPEG", quality=88, optimize=True)
    await state.update_data(pending_book_style=template_id)
    await callback.message.answer_photo(
        BufferedInputFile(buffer.getvalue(), filename=f"{template_id}.jpg"),
        caption=f"Preview: {template.label}",
        reply_markup=book_preview_menu(template_id),
    )
    await callback.answer()


@router.callback_query(BotStates.SETTING_BOOK, F.data.startswith("book:use:"))
async def use_builtin_book(callback: CallbackQuery, state: FSMContext, repo: UserRepository, settings: Settings) -> None:
    template_id = callback.data.rsplit(":", 1)[1]
    if template_id not in book_registry(settings.assets_dir.parent / "menu_buku"):
        await callback.answer("Template tidak ditemukan.", show_alert=True)
        return
    await repo.update(callback.from_user.id, book_style=template_id)
    await state.clear()
    await callback.message.answer("Template buku disimpan.", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(BotStates.SETTING_BOOK, F.data == "book:back")
async def back_to_books(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BotStates.SETTING_BOOK)
    await callback.message.answer("Pilih template buku:", reply_markup=books_menu())
    await callback.answer()


@router.callback_query(BotStates.SETTING_BOOK, F.data.startswith("book:"))
async def save_book(callback: CallbackQuery, state: FSMContext, repo: UserRepository) -> None:
    style = callback.data.split(":", 1)[1]
    if style == "custom":
        await state.set_state(BotStates.SETTING_CUSTOM_BOOK)
        await callback.message.answer("Kirim template sebagai gambar PNG/JPG. Gambar akan disesuaikan ke ukuran A4.")
    else:
        await repo.update(callback.from_user.id, book_style=style)
        await state.clear()
        await callback.message.answer("Template buku disimpan.", reply_markup=main_menu())
    await callback.answer()


def _normalize_template(data: bytes, target) -> None:
    with Image.open(BytesIO(data)) as image:
        if image.width < 800 or image.height < 1000:
            raise ValueError("Resolusi template terlalu kecil (minimal 800×1000 px).")
        image.convert("RGB").resize((2480, 3508), Image.Resampling.LANCZOS).save(target, "PNG", optimize=True)


@router.message(BotStates.SETTING_CUSTOM_BOOK, F.photo | F.document)
async def custom_book(message: Message, state: FSMContext, repo: UserRepository, settings: Settings) -> None:
    file = message.photo[-1] if message.photo else message.document
    if message.document and message.document.mime_type not in {"image/png", "image/jpeg"}:
        await message.answer("Format harus PNG atau JPG.")
        return
    if file.file_size and file.file_size > 12_000_000:
        await message.answer("Template terlalu besar. Maksimal 12 MB.")
        return
    buffer = BytesIO()
    await message.bot.download(file, destination=buffer)
    target = settings.assets_dir / "papers" / "custom" / f"{message.from_user.id}.png"
    try:
        await asyncio.to_thread(_normalize_template, buffer.getvalue(), target)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        await message.answer(str(exc) if isinstance(exc, ValueError) else "File gambar tidak valid.")
        return
    await repo.update(message.from_user.id, book_style=f"custom:{message.from_user.id}")
    await state.clear()
    await message.answer("Template custom disimpan.", reply_markup=main_menu())
