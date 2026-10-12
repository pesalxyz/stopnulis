from __future__ import annotations

from datetime import datetime


def parse_identity(text: str) -> dict[str, str]:
    lines = [line.strip() for line in text.splitlines()]
    if len(lines) != 4 or any(not line for line in lines):
        raise ValueError("Identitas harus terdiri dari tepat 4 baris: Nama, NPM, Kelas, dan Absen.")
    if len(lines[0]) > 100 or any(len(line) > 60 for line in lines[1:]):
        raise ValueError("Salah satu data identitas terlalu panjang.")
    return {"name": lines[0], "npm": lines[1], "class_name": lines[2], "attendance_number": lines[3]}


def validate_date(value: str) -> str:
    try:
        parsed = datetime.strptime(value.strip(), "%d-%m-%Y")
    except ValueError as exc:
        raise ValueError("Tanggal tidak valid. Gunakan format DD-MM-YYYY, misalnya 07-10-2026.") from exc
    return parsed.strftime("%d-%m-%Y")

