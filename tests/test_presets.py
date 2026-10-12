from pathlib import Path

from database.models import UserPreferences
from services.generation_service import GenerationService


ROOT = Path(__file__).resolve().parents[1]


def test_neat_presets_share_layout_but_differ_pixels() -> None:
    service = GenerationService(ROOT / "assets")
    preferences = UserPreferences(telegram_user_id=77, show_date=False, date_mode="none")
    results = [service.render("Mahasiswa menulis catatan yang rapi dan mudah dibaca.", preferences, seed=77, variation_level=level) for level in (0.05, 0.10, 0.15)]
    assert all(len(result.pages) == 1 for result in results)
    assert len({result.pages[0].size for result in results}) == 1
    assert len({result.pages[0].tobytes() for result in results}) == 3
