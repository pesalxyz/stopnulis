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


def identity_confirmation() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Konfirmasi", callback_data="identity:confirm"),
         InlineKeyboardButton(text="✏️ Edit Identitas", callback_data="identity:edit")],
        [InlineKeyboardButton(text="🙈 Lewati Identitas", callback_data="identity:skip")],
    ])


def format_preview(items: list[dict[str, str]]) -> str:
    if not items:
        return "(Identitas kosong — tidak akan ditulis)"
    return "\n".join(f"{item['label']}: {item['value']}" for item in items)


@router.callback_query(F.data == "menu:identity")
async def identity(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BotStates.SETTING_IDENTITY)
    await callback.message.answer("Atur identitas yang tampil di bagian atas halaman:", reply_markup=identity_menu())
    await callback.answer()


@router.callback_query(BotStates.SETTING_IDENTITY, F.data.in_({"identity:show", "identity:hide"}))
async def toggle_identity(callback: CallbackQuery, state: FSMContext, repo: UserRepository) -> None:
    show = callback.data.endswith("show")
    pref = await repo.get_or_create(callback.from_user.id)
    if show and not (pref.identity or pref.name):
        await callback.answer("Isi data identitas terlebih dahulu.", show_alert=True)
        return
    await repo.update(callback.from_user.id, show_identity=show)
    await state.clear()
    await callback.message.answer("Pengaturan identitas disimpan.", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(BotStates.SETTING_IDENTITY, F.data == "identity:edit")
@router.callback_query(BotStates.CONFIRMING_IDENTITY, F.data == "identity:edit")
async def edit_identity(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BotStates.SETTING_IDENTITY)
    await callback.message.answer(
        "Silakan kirim identitas yang ingin ditulis.\n\n"
        "Kamu bebas menentukan jenis dan jumlah identitas.\n"
        "Contoh:\nNama: Faisal Hidayat\nKelas: 9F\nWali Kelas: Bu Rini\n\n"
        "Boleh satu atau beberapa identitas. Gunakan format Label: Isi.\n"
        "Format lama empat baris tanpa label juga tetap didukung."
    )
    await callback.answer()


@router.message(BotStates.SETTING_IDENTITY, F.text)
async def save_identity(message: Message, state: FSMContext, repo: UserRepository) -> None:
    try:
        values = parse_identity(message.text)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await state.update_data(pending_identity=values)
    await state.set_state(BotStates.CONFIRMING_IDENTITY)
    await message.answer(
        "Preview identitas:\n\n" + format_preview(values["identity"]) +
        "\n\nPilih Konfirmasi, Edit, atau Lewati.", reply_markup=identity_confirmation())


@router.callback_query(BotStates.CONFIRMING_IDENTITY, F.data == "identity:confirm")
async def confirm_identity(callback: CallbackQuery, state: FSMContext, repo: UserRepository) -> None:
    data = await state.get_data()
    values = data.get("pending_identity") or {"identity": [], "identity_json": "[]"}
    values = {key: value for key, value in values.items() if key != "identity"}
    await repo.update(callback.from_user.id, **values, show_identity=bool(data.get("pending_identity", {}).get("identity")))
    await state.clear()
    await callback.message.answer("Identitas disimpan.", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(BotStates.CONFIRMING_IDENTITY, F.data == "identity:skip")
async def skip_identity(callback: CallbackQuery, state: FSMContext, repo: UserRepository) -> None:
    await repo.update(callback.from_user.id, identity_json="[]", name=None, npm=None,
                      class_name=None, attendance_number=None, show_identity=False)
    await state.clear()
    await callback.message.answer("Identitas dilewati.", reply_markup=main_menu())
    await callback.answer()
