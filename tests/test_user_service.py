import pytest

from services.user_service import parse_identity, validate_date


def test_parse_identity() -> None:
    result = parse_identity("Faisal Hidayat Sukma\n2310631250053\n7A Sistem Informasi\n12")
    assert result["name"] == "Faisal Hidayat Sukma"
    assert result["attendance_number"] == "12"
    assert result["identity"][0] == {"label": "Nama", "value": "Faisal Hidayat Sukma"}


@pytest.mark.parametrize("text, count", [
    ("Nama: Faisal", 1),
    ("Nama: Faisal\nKelas: 9F", 2),
    ("Nama: Faisal Hidayat\nKelas: 9F\nWali Kelas: Bu Rini", 3),
    ("Sekolah: SMP Negeri 1\nMata Pelajaran: Matematika\nKelompok: 3", 3),
])
def test_dynamic_identity(text: str, count: int) -> None:
    result = parse_identity(text)
    assert len(result["identity"]) == count


def test_empty_identity_is_valid() -> None:
    assert parse_identity("   ")["identity"] == []


def test_invalid_identity_requires_label() -> None:
    with pytest.raises(ValueError):
        parse_identity("Nama Faisal")


def test_long_identity_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_identity("Nama: " + "x" * 161)


@pytest.mark.parametrize("value", ["31-02-2026", "2026-10-07", "abc"])
def test_invalid_date(value: str) -> None:
    with pytest.raises(ValueError):
        validate_date(value)


def test_valid_date() -> None:
    assert validate_date("07-10-2026") == "07-10-2026"
