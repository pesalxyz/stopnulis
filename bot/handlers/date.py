from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.keyboards.main import main_menu
from bot.states.states import BotStates
from database.repository import UserRepository
from services.user_service import validate_date

router = Router(name="date")


def date_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Hari ini", callback_data="date:today"), InlineKeyboardButton(text="Custom", callback_data="date:custom")],
        [InlineKeyboardButton(text="Tidak ditampilkan", callback_data="date:none")],
        [InlineKeyboardButton(text="⬅️ Menu", callback_data="menu:main")],
    ])


@router.callback_query(F.data == "menu:date")
async def choose_date(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BotStates.SETTING_DATE)
    await callback.message.answer("Pilih pengaturan tanggal:", reply_markup=date_menu())
    await callback.answer()


@router.callback_query(BotStates.SETTING_DATE, F.data.in_({"date:today", "date:none"}))
async def save_date_mode(callback: CallbackQuery, state: FSMContext, repo: UserRepository) -> None:
    mode = callback.data.split(":", 1)[1]
    await repo.update(callback.from_user.id, date_mode=mode, show_date=mode != "none", custom_date=None)
    await state.clear()
    await callback.message.answer("Pengaturan tanggal disimpan.", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(BotStates.SETTING_DATE, F.data == "date:custom")
async def custom_date(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BotStates.SETTING_CUSTOM_DATE)
    await callback.message.answer("Kirim tanggal dengan format DD-MM-YYYY.")
    await callback.answer()


@router.message(BotStates.SETTING_CUSTOM_DATE, F.text)
async def save_custom_date(message: Message, state: FSMContext, repo: UserRepository) -> None:
    try:
        value = validate_date(message.text)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await repo.update(message.from_user.id, date_mode="custom", show_date=True, custom_date=value)
    await state.clear()
    await message.answer("Tanggal custom disimpan.", reply_markup=main_menu())

