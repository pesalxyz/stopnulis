from __future__ import annotations

import time
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.models import UserPreferences
from services.generation_service import GenerationService
TEXT = """Catatan Perkuliahan — Sistem Informasi, 7 Oktober 2026

Mahasiswa belajar merancang sistem yang rapi, efisien, dan mudah digunakan. Dalam pengembangan perangkat lunak, kita perlu memperhatikan kebutuhan pengguna, alur data, serta keamanan informasi. Angka pengujian: 10, 25, 48, dan 100%. Pertanyaan pentingnya: apakah hasil ini sudah natural?

Yang sering dilupakan adalah konsistensi. Dengan latihan berulang-ulang, tulisan akan tetap terbaca tanpa terasa terlalu sempurna. Kombinasi ng, ny, an, in, en, er, ar, ra, ri, si, ti, di, ke, me, pe, ber, ter, kan, yang, dan harus mengalir secara wajar.

Simbol uji: (A+B) = C; nilai #1 @ kelas — benar/salah? "Ya", jawabnya!"""


def render(style: str, destination: Path) -> tuple[float, dict[str, float | int] | None]:
    service = GenerationService(ROOT / "assets")
    preferences = UserPreferences(
        telegram_user_id=1,
        handwriting_style=style,
        ink_color="blue",
        show_identity=False,
        show_date=False,
        date_mode="none",
    )
    started = time.perf_counter()
    result = service.render(TEXT, preferences, seed=20261007)
    elapsed = time.perf_counter() - started
    result.pages[0].convert("RGB").save(destination, "PNG", optimize=True)
    return elapsed, result.debug_stats


def main() -> None:
    output = ROOT / "outputs"
    output.mkdir(exist_ok=True)
    before, _ = render("student", output / "before.png")
    after, stats = render("natural_student_01", output / "after.png")
    (output / "reference_test.png").write_bytes((output / "after.png").read_bytes())
    (output / "phase2_after.png").write_bytes((output / "after.png").read_bytes())
    (output / "phase3_metrics.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"before={before:.3f}s after={after:.3f}s")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
