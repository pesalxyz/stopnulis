from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.keyboards.main import main_menu
from bot.states.states import BotStates
from database.repository import UserRepository
from services.user_service import parse_identity

router = Router(name="identity")


def identity_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Isi/Ubah", callback_data="identity:edit")],
        [InlineKeyboardButton(text="👁 Tampilkan", callback_data="identity:show"), InlineKeyboardButton(text="🙈 Sembunyikan", callback_data="identity:hide")],
        [InlineKeyboardButton(text="⬅️ Menu", callback_data="menu:main")],
    ])


@router.callback_query(F.data == "menu:identity")
async def identity(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BotStates.SETTING_IDENTITY)
    await callback.message.answer("Atur identitas yang tampil di bagian atas halaman:", reply_markup=identity_menu())
    await callback.answer()


@router.callback_query(BotStates.SETTING_IDENTITY, F.data.in_({"identity:show", "identity:hide"}))
async def toggle_identity(callback: CallbackQuery, state: FSMContext, repo: UserRepository) -> None:
    show = callback.data.endswith("show")
    pref = await repo.get_or_create(callback.from_user.id)
    if show and not pref.name:
        await callback.answer("Isi data identitas terlebih dahulu.", show_alert=True)
        return
    await repo.update(callback.from_user.id, show_identity=show)
    await state.clear()
    await callback.message.answer("Pengaturan identitas disimpan.", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(BotStates.SETTING_IDENTITY, F.data == "identity:edit")
async def edit_identity(callback: CallbackQuery) -> None:
    await callback.message.answer("Kirim tepat 4 baris:\nNama\nNPM\nKelas\nAbsen")
    await callback.answer()


@router.message(BotStates.SETTING_IDENTITY, F.text)
async def save_identity(message: Message, state: FSMContext, repo: UserRepository) -> None:
    try:
        values = parse_identity(message.text)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await repo.update(message.from_user.id, **values, show_identity=True)
    await state.clear()
    await message.answer("Identitas disimpan dan akan ditampilkan.", reply_markup=main_menu())

