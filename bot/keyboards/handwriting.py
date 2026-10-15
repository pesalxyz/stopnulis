from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def handwriting_menu() -> InlineKeyboardMarkup:
    choices = [
        ("Agak Berantakan", "natural_student_01"),
        ("Rapih", "natural_student_upright_01"),
        ("Authentic Student Handwriting", "authentic_student_handwriting_01"),
    ]
    rows = [[InlineKeyboardButton(text=label, callback_data=f"handwriting:{key}")] for label, key in choices]
    rows.append([InlineKeyboardButton(text="⬅️ Menu", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
