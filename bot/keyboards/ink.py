from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def ink_menu() -> InlineKeyboardMarkup:
    choices = [("🔵 Biru", "blue"), ("⚫ Hitam", "black"), ("🔴 Merah", "red"), ("🟣 Ungu", "purple")]
    rows = [[InlineKeyboardButton(text=label, callback_data=f"ink:{key}")] for label, key in choices]
    rows.append([InlineKeyboardButton(text="⬅️ Menu", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

