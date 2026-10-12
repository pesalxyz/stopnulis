from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.keyboards.ink import ink_menu
from bot.keyboards.main import main_menu
from bot.states.states import BotStates
from config.settings import INK_COLORS
from database.repository import UserRepository

router = Router(name="ink")


@router.callback_query(F.data == "menu:ink")
async def choose_ink(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BotStates.SETTING_INK)
    await callback.message.answer("Pilih warna tinta:", reply_markup=ink_menu())
    await callback.answer()


@router.callback_query(BotStates.SETTING_INK, F.data.startswith("ink:"))
async def save_ink(callback: CallbackQuery, state: FSMContext, repo: UserRepository) -> None:
    color = callback.data.split(":", 1)[1]
    if color not in INK_COLORS:
        await callback.answer("Warna tidak dikenal.", show_alert=True)
        return
    await repo.update(callback.from_user.id, ink_color=color)
    await state.clear()
    await callback.message.answer("Warna tinta disimpan.", reply_markup=main_menu())
    await callback.answer()

