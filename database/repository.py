from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json

from database.db import Database
from database.models import GenerationHistory, UserPreferences


PREF_FIELDS = (
    "book_style", "handwriting_style", "ink_color", "show_identity", "name", "npm",
    "class_name", "attendance_number", "show_date", "date_mode", "custom_date",
    "identity_json",
)


class UserRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def get_or_create(self, telegram_user_id: int) -> UserPreferences:
        async with self.database.connect() as db:
            db.row_factory = __import__("sqlite3").Row
            await db.execute(
                "INSERT OR IGNORE INTO user_preferences (telegram_user_id) VALUES (?)",
                (telegram_user_id,),
            )
            await db.commit()
            async with db.execute("SELECT * FROM user_preferences WHERE telegram_user_id = ?", (telegram_user_id,)) as cur:
                row = await cur.fetchone()
        assert row is not None
        values = dict(row)
        raw_identity = values.pop("identity_json", None)
        try:
            values["identity"] = json.loads(raw_identity) if raw_identity else None
        except (TypeError, json.JSONDecodeError):
            values["identity"] = None
        values["show_identity"] = bool(values["show_identity"])
        values["show_date"] = bool(values["show_date"])
        for key in ("created_at", "updated_at"):
            if values.get(key):
                values[key] = datetime.fromisoformat(values[key])
        return UserPreferences(**values)

    async def update(self, telegram_user_id: int, **changes: object) -> UserPreferences:
        invalid = set(changes) - set(PREF_FIELDS)
        if invalid:
            raise ValueError(f"Kolom preferensi tidak dikenal: {', '.join(sorted(invalid))}")
        await self.get_or_create(telegram_user_id)
        if changes:
            assignments = ", ".join(f"{key} = ?" for key in changes)
            values = [int(v) if isinstance(v, bool) else v for v in changes.values()]
            async with self.database.connect() as db:
                await db.execute(
                    f"UPDATE user_preferences SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE telegram_user_id = ?",
                    (*values, telegram_user_id),
                )
                await db.commit()
        return await self.get_or_create(telegram_user_id)

    async def reset(self, telegram_user_id: int) -> UserPreferences:
        async with self.database.connect() as db:
            await db.execute("DELETE FROM user_preferences WHERE telegram_user_id = ?", (telegram_user_id,))
            await db.commit()
        return await self.get_or_create(telegram_user_id)

    async def add_history(self, history: GenerationHistory) -> None:
        async with self.database.connect() as db:
            await db.execute(
                "INSERT INTO generation_history (telegram_user_id, text_hash, page_count, output_type) VALUES (?, ?, ?, ?)",
                (history.telegram_user_id, history.text_hash, history.page_count, history.output_type),
            )
            await db.commit()
