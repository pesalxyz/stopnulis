from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def handwriting_menu() -> InlineKeyboardMarkup:
    choices = [("Natural Student", "natural_student_neat_90"), ("Natural Student Upright", "natural_student_upright_01"), ("Rapi", "neat"), ("Semi Rapi", "semi_neat"), ("Mahasiswa", "student"), ("Miring", "slanted"), ("Agak Berantakan", "messy")]
    rows = [[InlineKeyboardButton(text=label, callback_data=f"handwriting:{key}")] for label, key in choices]
    rows.append([InlineKeyboardButton(text="⬅️ Menu", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
