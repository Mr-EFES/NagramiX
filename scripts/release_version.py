"""Нумерация выпусков:0.9.9 →1.0 →1.0.1…1.0.9 →1.1."""
import re

_NUMBER = r"(?:0|[1-9][0-9]*)"
_VERSION = re.compile(rf"{_NUMBER}\.{_NUMBER}(?:\.{_NUMBER})?")


def parse_release_version(value: str) -> tuple[int, int, int]:
    """Сравнение двух/трёх частей; исторические IPA-контракты сохраняются."""
    if not isinstance(value, str) or _VERSION.fullmatch(value) is None:
        raise ValueError("Неверный номер версии: ожидается X.Y или X.Y.Z")
    parts = tuple(map(int, value.split('.')))
    return parts if len(parts) == 3 else (*parts, 0)


def is_release_version(value: str) -> bool:
    try:
        major, minor, patch = parse_release_version(value)
    except ValueError:
        return False
    if minor > 9 or patch > 9:
        return False
    # До1.0 сохраняется прежняя запись0.X.Y; затем нулевой patch опускается.
    if major == 0:
        return len(value.split('.')) == 3
    return len(value.split('.')) == 2 or patch > 0


def next_release_version(value: str) -> str:
    if not is_release_version(value):
        raise ValueError("Номер выпуска не соответствует утверждённой схеме")
    major, minor, patch = parse_release_version(value)
    patch += 1
    if patch == 10:
        minor, patch = minor + 1, 0
    if minor == 10:
        major, minor = major + 1, 0
    return f"{major}.{minor}" if major >= 1 and patch == 0 else f"{major}.{minor}.{patch}"
