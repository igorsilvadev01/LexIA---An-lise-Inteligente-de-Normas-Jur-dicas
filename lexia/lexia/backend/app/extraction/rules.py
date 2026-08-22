"""Extrator determinístico baseado em regras (baseline).

Por que existir se há um LLM? Três razões práticas:

1. **Baseline honesto** — sem baseline não é possível dizer se o LLM ajuda.
   Ele é medido pelo mesmo harness (`app.evaluation`) e pelo mesmo schema.
2. **Custo/latência zero e determinismo** — roda em CI, sem chave de API,
   sempre com o mesmo resultado.
3. **Fallback** — se o provedor de LLM falhar, a API continua respondendo.
"""

from __future__ import annotations

import re

from ..chunking import article_segments
from ..dates import parse_pt_date
from ..models import Deadline, LegalNorm, Obligation, Penalty
from ..text import sentences, strip_accents

NORM_TYPES: list[tuple[str, str]] = [
    ("instrucao normativa", "instrucao_normativa"),
    ("medida provisoria", "medida_provisoria"),
    ("resolucao", "resolucao"),
    ("portaria", "portaria"),
    ("decreto", "decreto"),
    ("lei", "lei"),
]

DISPLAY_TYPES: dict[str, str] = {
    "instrucao_normativa": "Instrução Normativa",
    "medida_provisoria": "Medida Provisória",
    "resolucao": "Resolução",
    "portaria": "Portaria",
    "decreto": "Decreto",
    "lei": "Lei",
}

HEADER_RE = re.compile(
    r"\b(instrucao normativa|medida provisoria|resolucao|portaria|decreto|lei)\b"
    r"(?:\s+complementar)?\s*(?:n[.\u00ba\u00b0o]*\s*)?([\d][\d.]*)",
    re.IGNORECASE,
)

REFERENCE_RE = re.compile(
    r"\b(instrucao normativa|medida provisoria|resolucao|portaria|decreto|lei)\b"
    r"\s*(?:n[.\u00ba\u00b0o]*\s*)?([\d][\d.]*)\s*(?:,\s*)?"
    r"(?:de\s+\d{1,2}[\u00bao\u00b0]?\s+de\s+[a-z]+\s+de\s+(\d{4})|de\s+(\d{4})|/\s*(\d{4}))",
    re.IGNORECASE,
)

BODY_KEYWORDS = (
    "presidencia",
    "ministerio",
    "agencia",
    "secretaria",
    "conselho",
    "banco central",
    "comissao",
    "instituto",
    "tribunal",
    "autoridade nacional",
    "diretoria",
)

EMENTA_STARTERS = (
    "dispoe sobre",
    "estabelece",
    "regulamenta",
    "institui",
    "altera",
    "aprova",
    "define",
    "fixa",
    "disciplina",
)

# Marcadores deônticos. Usamos limites de palavra para não capturar
# substantivos como "DEVERES" em cabeçalhos ('DOS DEVERES DOS ÓRGÃOS').
OBLIGATION_RE = re.compile(
    r"\b(?:deverao|devera|devem|deve)\b|\bfica[m]?\s+obrigad|\bobriga-se\b|\be\s+obrigatori[ao]\b",
    re.IGNORECASE,
)

DEADLINE_UNITS: dict[str, str] = {
    "dia": "dias",
    "dias": "dias",
    "mes": "meses",
    "meses": "meses",
    "ano": "anos",
    "anos": "anos",
    "hora": "horas",
    "horas": "horas",
}

DEADLINE_RE = re.compile(
    r"(\d+)\s*(?:\([^)]*\)\s*)?(dias|dia|meses|mes|anos|ano|horas|hora)\b",
    re.IGNORECASE,
)

DEADLINE_CONTEXT = ("prazo", "no minimo", "no maximo", "periodo", "contado", "por dia")

PENALTY_KINDS: list[tuple[str, str]] = [
    ("multa", "multa"),
    ("advertencia", "advertencia"),
    ("suspensao", "suspensao"),
    ("suspender", "suspensao"),
    ("cassacao", "cassacao"),
    ("sancao", "outra"),
    ("penalidade", "outra"),
]

MONEY_RE = re.compile(r"R\$\s?[\d.]+(?:,\d{2})?", re.IGNORECASE)
PERCENT_RE = re.compile(r"\d+(?:,\d+)?\s*%\s*(?:\([^)]*\)\s*)?(?:do faturamento[^,.;]*)?", re.IGNORECASE)


def _fold(value: str) -> str:
    return strip_accents(value).lower()


def _clean(value: str) -> str:
    value = re.sub(r"^\s*Art(?:igo)?\.?\s*\d+\s*[\u00bao\u00b0]?\s*", "", value).strip()
    value = re.sub(r"^[IVXLC]+\s*-\s*", "", value).strip()
    return re.sub(r"\s+", " ", value).strip(" -–—")


def _is_heading(sentence: str) -> bool:
    """Cabeçalhos estruturais (CAPÍTULO/TÍTULO em caixa alta) não são normas."""
    stripped = sentence.strip()
    if not stripped:
        return True
    letters = [ch for ch in stripped if ch.isalpha()]
    return bool(letters) and all(ch.isupper() for ch in letters)


def _preamble(text: str) -> str:
    segments = article_segments(text)
    if segments and segments[0][2] is None:
        start, end, _ = segments[0]
        return text[start:end]
    return text[:1500]


def _extract_header(preamble: str) -> tuple[str, str | None, str | None]:
    folded = _fold(preamble)
    match = HEADER_RE.search(folded)
    if not match:
        return "desconhecido", None, None
    raw_type = match.group(1)
    norm_type = next((value for key, value in NORM_TYPES if key == raw_type), "desconhecido")
    number = match.group(2).strip(".")
    line_end = preamble.find("\n", match.start())
    header_line = preamble[match.start() : line_end if line_end != -1 else len(preamble)]
    return norm_type, number, parse_pt_date(header_line)


def _extract_issuing_body(preamble: str) -> str | None:
    for line in preamble.split("\n"):
        stripped = line.strip()
        if len(stripped) < 6:
            continue
        folded = _fold(stripped)
        if any(keyword in folded for keyword in BODY_KEYWORDS) and not HEADER_RE.match(folded):
            if folded.startswith("o ") or folded.startswith("a "):
                continue  # linha de preâmbulo ("O PRESIDENTE ... decreta")
            return re.sub(r"\s+", " ", stripped)
    return None


def _extract_subject(preamble: str) -> str | None:
    for block in preamble.split("\n"):
        candidate = block.strip()
        if len(candidate) < 20:
            continue
        folded = _fold(candidate)
        if any(folded.startswith(starter) for starter in EMENTA_STARTERS):
            return re.sub(r"\s+", " ", candidate)
    return None


def _extract_references(text: str, norm_type: str, number: str | None) -> list[str]:
    seen: dict[str, None] = {}
    self_key = f"{norm_type}:{number}" if number else None
    for match in REFERENCE_RE.finditer(_fold(text)):
        raw_type = match.group(1)
        kind = next((value for key, value in NORM_TYPES if key == raw_type), None)
        if kind is None:
            continue
        num = match.group(2).strip(".")
        year = match.group(3) or match.group(4) or match.group(5)
        if not year:
            continue
        if self_key and f"{kind}:{num}" == self_key:
            continue
        seen.setdefault(f"{DISPLAY_TYPES[kind]} nº {num}/{year}", None)
    return list(seen)


def _actor_and_action(sentence: str, marker_pos: int) -> tuple[str | None, str]:
    actor = _clean(sentence[:marker_pos])
    action = re.sub(r"\s+", " ", sentence[marker_pos:]).strip()
    if not actor or len(actor) > 120:
        return None, _clean(sentence)
    return actor, action


def _extract_deadlines(sentence: str, article: str | None) -> list[Deadline]:
    folded = _fold(sentence)
    if not any(marker in folded for marker in DEADLINE_CONTEXT):
        return []
    found: list[Deadline] = []
    for match in DEADLINE_RE.finditer(folded):
        unit = DEADLINE_UNITS.get(match.group(2))
        if unit is None:
            continue
        found.append(
            Deadline(
                description=_clean(sentence),
                value=int(match.group(1)),
                unit=unit,  # type: ignore[arg-type]
                article=article,
                evidence=sentence.strip(),
            )
        )
    return found


def _extract_penalties(sentence: str, article: str | None) -> list[Penalty]:
    folded = _fold(sentence)
    kinds: list[str] = []
    for keyword, kind in PENALTY_KINDS:
        if keyword in folded and kind not in kinds:
            kinds.append(kind)
    if not kinds:
        return []
    money = MONEY_RE.search(sentence)
    percent = PERCENT_RE.search(sentence)
    amount = money.group(0) if money else (percent.group(0).strip() if percent else None)
    return [
        Penalty(
            description=_clean(sentence),
            kind=kind,  # type: ignore[arg-type]
            amount=amount if kind == "multa" else None,
            article=article,
            evidence=sentence.strip(),
        )
        for kind in kinds
    ]


def extract(text: str) -> tuple[LegalNorm, list[str]]:
    """Extrai a norma estruturada e uma lista de avisos de baixa confiança."""
    warnings: list[str] = []
    preamble = _preamble(text)

    norm_type, number, publication_date = _extract_header(preamble)
    if norm_type == "desconhecido":
        warnings.append("cabeçalho não reconhecido: tipo/número da norma indefinidos")

    norm = LegalNorm(
        norm_type=norm_type,  # type: ignore[arg-type]
        number=number,
        year=int(publication_date[:4]) if publication_date else None,
        issuing_body=_extract_issuing_body(preamble),
        publication_date=publication_date,
        subject=_extract_subject(preamble),
        references=_extract_references(text, norm_type, number),
    )
    if norm.subject is None:
        warnings.append("ementa não localizada no preâmbulo")

    seen_deadlines: set[tuple[int | None, str, str | None]] = set()
    seen_penalties: set[tuple[str, str | None]] = set()

    for start, end, article in article_segments(text):
        segment = text[start:end]
        for sentence in sentences(segment):
            folded = _fold(sentence)

            if _is_heading(sentence):
                continue

            marker = OBLIGATION_RE.search(folded)
            marker_pos = marker.start() if marker else -1
            if marker_pos != -1 and article is not None:
                actor, action = _actor_and_action(sentence, marker_pos)
                norm.obligations.append(
                    Obligation(actor=actor, action=action, article=article, evidence=sentence.strip())
                )

            for deadline in _extract_deadlines(sentence, article):
                key = (deadline.value, deadline.unit, deadline.article)
                if key not in seen_deadlines:
                    seen_deadlines.add(key)
                    norm.deadlines.append(deadline)

            for penalty in _extract_penalties(sentence, article):
                key = (penalty.kind, penalty.article)
                if key not in seen_penalties:
                    seen_penalties.add(key)
                    norm.penalties.append(penalty)

            if "entra em vigor" in folded and norm.effective_date is None:
                norm.effective_date = parse_pt_date(sentence) or (
                    norm.publication_date if "data de sua publicacao" in folded else None
                )

    if norm.effective_date is None:
        warnings.append("cláusula de vigência não encontrada")
    return norm, warnings
