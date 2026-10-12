from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.keyboards.handwriting import handwriting_menu
from bot.keyboards.main import main_menu
from bot.states.states import BotStates
from config.settings import HANDWRITING_STYLES
from database.repository import UserRepository

router = Router(name="handwriting")


@router.callback_query(F.data == "menu:handwriting")
async def choose_style(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BotStates.SETTING_HANDWRITING)
    await callback.message.answer("Pilih gaya tulisan:", reply_markup=handwriting_menu())
    await callback.answer()


@router.callback_query(BotStates.SETTING_HANDWRITING, F.data.startswith("handwriting:"))
async def save_style(callback: CallbackQuery, state: FSMContext, repo: UserRepository) -> None:
    style = callback.data.split(":", 1)[1]
    if style not in HANDWRITING_STYLES:
        await callback.answer("Gaya tidak dikenal.", show_alert=True)
        return
    await repo.update(callback.from_user.id, handwriting_style=style)
    await state.clear()
    await callback.message.answer("Gaya tulisan disimpan.", reply_markup=main_menu())
    await callback.answer()

