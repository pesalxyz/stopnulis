from __future__ import annotations

from datetime import datetime
import json

MAX_IDENTITY_FIELDS = 12
MAX_IDENTITY_LABEL = 40
MAX_IDENTITY_VALUE = 160


def identity_for_preferences(identity: list[dict[str, str]] | None, name: str | None = None,
                             npm: str | None = None, class_name: str | None = None,
                             attendance_number: str | None = None) -> list[dict[str, str]]:
    if identity:
        return identity
    legacy = (("Nama", name), ("NPM", npm), ("Kelas", class_name), ("Absen", attendance_number))
    return [{"label": label, "value": value} for label, value in legacy if value]


def parse_identity(text: str) -> dict[str, object]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return {"identity": [], "identity_json": "[]", "name": None, "npm": None,
                "class_name": None, "attendance_number": None}
    if len(lines) > MAX_IDENTITY_FIELDS:
        raise ValueError(f"Identitas maksimal {MAX_IDENTITY_FIELDS} baris.")
    # Preserve the old four-line format (without labels).
    if len(lines) == 4 and all(":" not in line for line in lines):
        pairs = list(zip(("Nama", "NPM", "Kelas", "Absen"), lines))
    else:
        pairs = []
        for line in lines:
            if ":" not in line:
                raise ValueError("Gunakan format 'Label: Isi' untuk setiap baris identitas.")
            label, value = (part.strip() for part in line.split(":", 1))
            if not label or not value:
                raise ValueError("Label dan isi identitas tidak boleh kosong.")
            pairs.append((label, value))
    identity = []
    for label, value in pairs:
        if len(label) > MAX_IDENTITY_LABEL or len(value) > MAX_IDENTITY_VALUE:
            raise ValueError("Label maksimal 40 karakter dan isi maksimal 160 karakter.")
        identity.append({"label": label, "value": value})
    canonical = {item["label"].casefold(): item["value"] for item in identity}
    return {
        "identity": identity,
        "identity_json": json.dumps(identity, ensure_ascii=False),
        "name": canonical.get("nama"), "npm": canonical.get("npm"),
        "class_name": canonical.get("kelas"), "attendance_number": canonical.get("absen"),
    }


def validate_date(value: str) -> str:
    try:
        parsed = datetime.strptime(value.strip(), "%d-%m-%Y")
    except ValueError as exc:
        raise ValueError("Tanggal tidak valid. Gunakan format DD-MM-YYYY, misalnya 07-10-2026.") from exc
    return parsed.strftime("%d-%m-%Y")
