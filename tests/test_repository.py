import pytest

from database.db import Database
from database.models import GenerationHistory
from database.repository import UserRepository


@pytest.mark.asyncio
async def test_user_preferences_roundtrip(tmp_path) -> None:
    database = Database(tmp_path / "test.db")
    await database.initialize()
    repo = UserRepository(database)
    original = await repo.get_or_create(123)
    assert original.book_style == "book_buku_tulis_1"
    updated = await repo.update(123, ink_color="purple", show_identity=True, name="Faisal")
    assert updated.ink_color == "purple"
    assert updated.show_identity is True
    reset = await repo.reset(123)
    assert reset.ink_color == "blue"


@pytest.mark.asyncio
async def test_dynamic_identity_roundtrip(tmp_path) -> None:
    database = Database(tmp_path / "dynamic.db")
    await database.initialize()
    repo = UserRepository(database)
    identity = [{"label": "Nama", "value": "Faisal"}, {"label": "Wali Kelas", "value": "Bu Rini"}]
    import json
    updated = await repo.update(456, identity_json=json.dumps(identity), show_identity=True)
    assert updated.identity == identity


@pytest.mark.asyncio
async def test_usage_stats_aggregate_accounts_and_generations(tmp_path) -> None:
    database = Database(tmp_path / "stats.db")
    await database.initialize()
    repo = UserRepository(database)
    await repo.get_or_create(123)
    await repo.get_or_create(456)
    await repo.add_history(GenerationHistory(123, "hash-a", 1, "png"))
    await repo.add_history(GenerationHistory(123, "hash-b", 2, "pdf"))
    stats = await repo.usage_stats()
    assert stats["total_users"] == 2
    assert stats["active_users"] == 1
    assert stats["total_generations"] == 2
    assert stats["active_today"] == 1
