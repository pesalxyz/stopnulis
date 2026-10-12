from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class UserPreferences:
    telegram_user_id: int
    book_style: str = "book_buku_tulis_1"
    handwriting_style: str = "natural_student_upright_01"
    ink_color: str = "blue"
    show_identity: bool = False
    name: str | None = None
    npm: str | None = None
    class_name: str | None = None
    attendance_number: str | None = None
    show_date: bool = True
    date_mode: str = "today"
    custom_date: str | None = None
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class GenerationHistory:
    telegram_user_id: int
    text_hash: str
    page_count: int
    output_type: str
    id: int | None = None
    created_at: datetime | None = None
