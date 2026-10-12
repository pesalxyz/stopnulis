from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, FSInputFile, Message

from bot.keyboards.main import main_menu, output_menu, preview_menu
from bot.states.states import BotStates
from config.settings import Settings
from database.models import GenerationHistory
from database.repository import UserRepository
from renderer.export import preview_bytes, save_pdf, save_png_pages
from services.generation_service import GenerationService

logger = logging.getLogger(__name__)
router = Router(name="generate")


@router.callback_query(F.data == "menu:write")
async def begin_writing(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BotStates.WAITING_TEXT)
    await callback.message.answer("Silakan kirim teks yang ingin ditulis.")
    await callback.answer()


async def _make_preview(message: Message, state: FSMContext, text: str, repo: UserRepository, generator: GenerationService) -> None:
    pref = await repo.get_or_create(message.from_user.id)
    try:
        result = await asyncio.to_thread(generator.render, text, pref, message.from_user.id, True)
        data = await asyncio.to_thread(preview_bytes, result.pages[0])
    except (ValueError, FileNotFoundError) as exc:
        await message.answer(str(exc))
        return
    except Exception:
        logger.exception("Preview render failed for user %s", message.from_user.id)
        await message.answer("Preview gagal dibuat. Silakan coba lagi.")
        return
    await state.update_data(source_text=text)
    await state.set_state(BotStates.PREVIEW)
    await message.answer_photo(
        BufferedInputFile(data, filename="preview.jpg"),
        caption="Preview halaman pertama. Hasil final menggunakan resolusi penuh.",
        reply_markup=preview_menu(),
    )


@router.message(BotStates.WAITING_TEXT, F.text)
async def receive_text(message: Message, state: FSMContext, repo: UserRepository, generator: GenerationService, settings: Settings) -> None:
    if len(message.text) > settings.max_text_length:
        await message.answer(f"Teks terlalu panjang. Maksimal {settings.max_text_length:,} karakter.")
        return
    await message.answer("Sedang membuat preview…")
    await _make_preview(message, state, message.text, repo, generator)


@router.callback_query(BotStates.PREVIEW, F.data == "preview:edit")
async def edit_text(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BotStates.WAITING_TEXT)
    await callback.message.answer("Silakan kirim teks pengganti.")
    await callback.answer()


@router.callback_query(BotStates.PREVIEW, F.data == "preview:cancel")
async def cancel_preview(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Penulisan dibatalkan.", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(BotStates.PREVIEW, F.data == "preview:generate")
async def select_output(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BotStates.SELECTING_OUTPUT)
    await callback.message.answer("Pilih format hasil final:", reply_markup=output_menu())
    await callback.answer()


@router.callback_query(BotStates.SELECTING_OUTPUT, F.data == "output:back")
async def back_to_preview(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BotStates.PREVIEW)
    await callback.message.answer("Pilih tindakan:", reply_markup=preview_menu())
    await callback.answer()


def _export(result, output_dir: Path, stem: str, output_type: str) -> list[Path]:
    if output_type == "pdf":
        return [save_pdf(result.pages, output_dir / f"{stem}.pdf")]
    return save_png_pages(result.pages, output_dir, stem)


@router.callback_query(BotStates.SELECTING_OUTPUT, F.data.in_({"output:png", "output:pdf"}))
async def generate_final(
    callback: CallbackQuery,
    state: FSMContext,
    repo: UserRepository,
    generator: GenerationService,
    settings: Settings,
) -> None:
    data = await state.get_data()
    text = data.get("source_text")
    if not text:
        await state.clear()
        await callback.message.answer("Teks tidak ditemukan. Silakan mulai lagi.", reply_markup=main_menu())
        await callback.answer()
        return
    output_type = callback.data.split(":", 1)[1]
    await callback.answer()
    status = await callback.message.answer("Sedang membuat hasil final…")
    pref = await repo.get_or_create(callback.from_user.id)
    stem = f"handwriting_{callback.from_user.id}_{uuid.uuid4().hex[:10]}"
    paths: list[Path] = []
    try:
        result = await asyncio.to_thread(generator.render, text, pref, callback.from_user.id, False)
        paths = await asyncio.to_thread(_export, result, settings.output_dir, stem, output_type)
        total_size = sum(path.stat().st_size for path in paths)
        if total_size > settings.max_output_bytes:
            raise ValueError("Ukuran hasil terlalu besar. Kurangi panjang teks atau gunakan PDF.")
        for path in paths:
            await callback.message.answer_document(FSInputFile(path), caption=f"Hasil {output_type.upper()}" if len(paths) == 1 else None)
        await repo.add_history(GenerationHistory(callback.from_user.id, result.text_hash, len(result.pages), output_type))
        await state.clear()
        await status.edit_text(f"Selesai — {len(result.pages)} halaman.")
        await callback.message.answer("Ingin menulis lagi?", reply_markup=main_menu())
    except (ValueError, FileNotFoundError) as exc:
        await status.edit_text(str(exc))
    except TelegramAPIError:
        logger.exception("Telegram upload failed for user %s", callback.from_user.id)
        await status.edit_text("Upload ke Telegram gagal. Silakan coba lagi.")
    except OSError:
        logger.exception("Storage/export failed for user %s", callback.from_user.id)
        await status.edit_text("Penyimpanan tidak tersedia atau penuh.")
    except Exception:
        logger.exception("Final generation failed for user %s", callback.from_user.id)
        await status.edit_text("Render gagal. Silakan coba lagi.")
    finally:
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not remove temporary output %s", path.name)

