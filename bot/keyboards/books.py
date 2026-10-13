from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config.settings import ROOT_DIR
from config.books import discover_book_templates


def books_menu() -> InlineKeyboardMarkup:
    templates = discover_book_templates(ROOT_DIR / "menu_buku")
    rows = [[InlineKeyboardButton(text=item.label, callback_data=f"book:{item.template_id}")] for item in templates]
    rows.append([InlineKeyboardButton(text="⬅️ Menu", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def book_preview_menu(template_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Gunakan Buku Ini", callback_data=f"book:use:{template_id}")],
        [InlineKeyboardButton(text="⬅️ Kembali", callback_data="book:back")],
    ])
