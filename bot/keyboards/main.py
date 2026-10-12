from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📚 Pilih Buku", callback_data="menu:book"), InlineKeyboardButton(text="✍️ Gaya Tulisan", callback_data="menu:handwriting")],
        [InlineKeyboardButton(text="👤 Identitas", callback_data="menu:identity"), InlineKeyboardButton(text="📅 Tanggal", callback_data="menu:date")],
        [InlineKeyboardButton(text="🖊 Tinta", callback_data="menu:ink"), InlineKeyboardButton(text="📝 Mulai Menulis", callback_data="menu:write")],
        [InlineKeyboardButton(text="⚙️ Pengaturan", callback_data="menu:settings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Menu", callback_data="menu:main")]])


def preview_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Generate", callback_data="preview:generate"), InlineKeyboardButton(text="✏️ Edit Text", callback_data="preview:edit")],
        [InlineKeyboardButton(text="🎨 Ubah Setting", callback_data="menu:main"), InlineKeyboardButton(text="❌ Batal", callback_data="preview:cancel")],
    ])


def output_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼 PNG", callback_data="output:png"), InlineKeyboardButton(text="📄 PDF", callback_data="output:pdf")],
        [InlineKeyboardButton(text="⬅️ Preview", callback_data="output:back")],
    ])

