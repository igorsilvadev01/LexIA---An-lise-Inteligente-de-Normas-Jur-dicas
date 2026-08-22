"""Parsing de datas em português para formato ISO-8601."""

from __future__ import annotations

import re

MONTHS: dict[str, int] = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

_LONG_RE = re.compile(
    r"(\d{1,2})\s*[ºo°]?\s*de\s+([a-zç]+)\s+de\s+(\d{4})",
    re.IGNORECASE,
)
_NUMERIC_RE = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b")


def _iso(day: int, month: int, year: int) -> str | None:
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_pt_date(value: str) -> str | None:
    """Extrai a primeira data reconhecível de `value` e devolve ISO-8601.

    Suporta "14 de agosto de 2018", "1º de janeiro de 2020" e "14/08/2018".
    """
    from .text import strip_accents

    folded = strip_accents(value).lower()
    match = _LONG_RE.search(folded)
    if match:
        month = MONTHS.get(match.group(2))
        if month:
            return _iso(int(match.group(1)), month, int(match.group(3)))
    match = _NUMERIC_RE.search(folded)
    if match:
        return _iso(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None
