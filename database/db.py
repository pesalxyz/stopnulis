from __future__ import annotations

from pathlib import Path

import aiosqlite


SCHEMA = """
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER NOT NULL UNIQUE,
    book_style TEXT NOT NULL DEFAULT 'book_buku_tulis_1',
    handwriting_style TEXT NOT NULL DEFAULT 'natural_student_upright_01',
    ink_color TEXT NOT NULL DEFAULT 'blue',
    show_identity INTEGER NOT NULL DEFAULT 0,
    name TEXT,
    npm TEXT,
    class_name TEXT,
    attendance_number TEXT,
    show_date INTEGER NOT NULL DEFAULT 1,
    date_mode TEXT NOT NULL DEFAULT 'today',
    custom_date TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS generation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER NOT NULL,
    text_hash TEXT NOT NULL,
    page_count INTEGER NOT NULL,
    output_type TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_history_user ON generation_history(telegram_user_id, created_at);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    def connect(self) -> aiosqlite.Connection:
        return aiosqlite.connect(self.path)
