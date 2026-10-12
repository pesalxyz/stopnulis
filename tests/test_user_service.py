import pytest

from services.user_service import parse_identity, validate_date


def test_parse_identity() -> None:
    result = parse_identity("Faisal Hidayat Sukma\n2310631250053\n7A Sistem Informasi\n12")
    assert result["name"] == "Faisal Hidayat Sukma"
    assert result["attendance_number"] == "12"


def test_parse_identity_rejects_incomplete() -> None:
    with pytest.raises(ValueError):
        parse_identity("Nama\nNPM")


@pytest.mark.parametrize("value", ["31-02-2026", "2026-10-07", "abc"])
def test_invalid_date(value: str) -> None:
    with pytest.raises(ValueError):
        validate_date(value)


def test_valid_date() -> None:
    assert validate_date("07-10-2026") == "07-10-2026"

