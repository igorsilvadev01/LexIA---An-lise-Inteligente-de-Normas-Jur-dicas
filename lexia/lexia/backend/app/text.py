"""Utilitários de normalização e tokenização de texto jurídico em português."""

from __future__ import annotations

import re
import unicodedata

# Stopwords enxutas: mantemos termos jurídicos relevantes (ex. "prazo", "multa")
# e removemos apenas conectivos de altíssima frequência.
STOPWORDS: frozenset[str] = frozenset(
    """
    a as o os um uma uns umas de do da dos das em no na nos nas ao aos à às
    e ou que se por para com sem sob sobre entre como quando onde qual quais
    seu sua seus suas este esta estes estas esse essa esses essas isto isso
    ser sao é eh foi sera serao ha havera tem tera pelo pela pelos pelas
    """.split()
)

_WORD_RE = re.compile(r"[0-9a-zà-öø-ÿ]+", re.IGNORECASE)
_WS_RE = re.compile(r"[ \t\u00a0]+")
_MULTINEWLINE_RE = re.compile(r"\n{3,}")


def strip_accents(value: str) -> str:
    """Remove acentos preservando os caracteres base."""
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def normalize_whitespace(value: str) -> str:
    """Colapsa espaços/hifenização de quebra de linha típica de PDFs."""
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"(\w)-\n(\w)", r"\1\2", value)  # hifenização de fim de linha
    value = _WS_RE.sub(" ", value)
    value = _MULTINEWLINE_RE.sub("\n\n", value)
    return "\n".join(line.strip() for line in value.split("\n")).strip()


def tokenize(value: str, *, remove_stopwords: bool = True) -> list[str]:
    """Tokenização determinística: minúsculas, sem acento, apenas alfanuméricos."""
    folded = strip_accents(value).lower()
    tokens = _WORD_RE.findall(folded)
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS]
    return tokens


def normalize_key(value: str) -> str:
    """Chave canônica para comparação de strings na avaliação (métricas)."""
    return " ".join(tokenize(value, remove_stopwords=False))


_ABBREVIATIONS = ("arts", "art", "artigo", "incs", "inc", "par", "n", "no", "nos", "sr", "sra", "dr", "dra")
_ABBR_RE = re.compile(r"\b(" + "|".join(_ABBREVIATIONS) + r")\.", re.IGNORECASE)


def sentences(value: str) -> list[str]:
    """Segmentação de sentenças tolerante a abreviações jurídicas ("Art. 3º")."""
    protected = _ABBR_RE.sub(lambda m: f"{m.group(1)}<DOT>", value)
    parts = re.split(r"(?<=[.!?;:])\s+", protected)
    return [p.replace("<DOT>", ".").strip() for p in parts if p.strip()]
