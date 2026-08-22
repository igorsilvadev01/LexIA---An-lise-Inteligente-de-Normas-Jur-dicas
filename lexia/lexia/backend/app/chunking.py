"""Chunking consciente da estrutura de normas jurídicas.

Diferente de um `split(1000)` genérico, o chunker respeita a unidade semântica
do texto legal: cada artigo (`Art. 1º`, `Art. 2º`, ...) vira um chunk, e apenas
artigos longos são subdivididos (com sobreposição) em janelas que quebram em
limites de parágrafo. Isso melhora a recuperação porque o modelo/consulta
raramente precisa de "meio artigo".
"""

from __future__ import annotations

import hashlib
import re

from .models import Chunk

ARTICLE_RE = re.compile(r"^\s*(Art(?:igo)?\.?\s*\d+\s*[ºo°]?(?:\-[A-Z])?)", re.MULTILINE | re.IGNORECASE)
SECTION_RE = re.compile(
    r"^\s*((?:CAP[ÍI]TULO|SE[ÇC][ÃA]O|T[ÍI]TULO|LIVRO|ANEXO)\s+[\wÀ-ÿ\-]+.*)$",
    re.MULTILINE | re.IGNORECASE,
)


def _normalize_article_label(raw: str) -> str:
    """'art 5' / 'Artigo 5º' -> 'Art. 5º' (rótulo canônico)."""
    number = re.search(r"\d+(?:\-[A-Z])?", raw)
    if not number:
        return raw.strip()
    return f"Art. {number.group(0)}º"


def chunk_id_for(document_id: str, ordinal: int, text: str) -> str:
    digest = hashlib.sha1(f"{document_id}:{ordinal}:{text}".encode()).hexdigest()[:10]
    return f"{document_id}-c{ordinal:03d}-{digest}"


def _section_at(sections: list[tuple[int, str]], position: int) -> str | None:
    current = None
    for start, label in sections:
        if start <= position:
            current = label
        else:
            break
    return current


def _segments(text: str) -> list[tuple[int, int, str | None]]:
    """Divide o texto em (start, end, rótulo do artigo)."""
    matches = list(ARTICLE_RE.finditer(text))
    if not matches:
        return [(0, len(text), None)]

    segments: list[tuple[int, int, str | None]] = []
    first_start = matches[0].start(1)
    if text[:first_start].strip():
        segments.append((0, first_start, None))
    for idx, match in enumerate(matches):
        start = match.start(1)
        end = matches[idx + 1].start(1) if idx + 1 < len(matches) else len(text)
        segments.append((start, end, _normalize_article_label(match.group(1))))
    return segments


def article_segments(text: str) -> list[tuple[int, int, str | None]]:
    """Segmentos ``(início, fim, rótulo do artigo)``; rótulo ``None`` no preâmbulo."""
    return _segments(text)


def _paragraph_spans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = start
    for line in re.split(r"(\n+)", text[start:end]):
        if not line:
            continue
        length = len(line)
        if line.strip():
            spans.append((cursor, cursor + length))
        cursor += length
    return spans or [(start, end)]


def _windows(start: int, end: int, max_chars: int, overlap: int) -> list[tuple[int, int]]:
    """Janelas fixas com sobreposição para parágrafos maiores que `max_chars`."""
    step = max(1, max_chars - overlap)
    out: list[tuple[int, int]] = []
    cursor = start
    while cursor < end:
        out.append((cursor, min(end, cursor + max_chars)))
        cursor += step
    return out


def chunk_text(
    text: str,
    document_id: str,
    *,
    max_chars: int = 1200,
    overlap: int = 120,
) -> list[Chunk]:
    """Gera chunks estáveis (ids determinísticos) para um documento normalizado."""
    if max_chars <= 0:
        raise ValueError("max_chars deve ser positivo")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap deve estar em [0, max_chars)")

    sections = [(m.start(1), m.group(1).strip()) for m in SECTION_RE.finditer(text)]
    chunks: list[Chunk] = []
    ordinal = 0

    for seg_start, seg_end, article in _segments(text):
        seg_text = text[seg_start:seg_end]
        if not seg_text.strip():
            continue

        if len(seg_text.strip()) <= max_chars:
            ranges = [(seg_start, seg_end)]
        else:
            ranges = []
            buffer_start: int | None = None
            buffer_end = seg_start
            for para_start, para_end in _paragraph_spans(text, seg_start, seg_end):
                para_len = para_end - para_start
                if para_len > max_chars:
                    if buffer_start is not None:
                        ranges.append((buffer_start, buffer_end))
                        buffer_start = None
                    ranges.extend(_windows(para_start, para_end, max_chars, overlap))
                    buffer_end = para_end
                    continue
                if buffer_start is None:
                    buffer_start = max(seg_start, para_start - overlap) if ranges else para_start
                    buffer_end = para_end
                elif para_end - buffer_start <= max_chars:
                    buffer_end = para_end
                else:
                    ranges.append((buffer_start, buffer_end))
                    buffer_start = max(seg_start, para_start - overlap)
                    buffer_end = para_end
            if buffer_start is not None:
                ranges.append((buffer_start, buffer_end))

        for start, end in ranges:
            body = text[start:end].strip()
            if not body:
                continue
            chunks.append(
                Chunk(
                    id=chunk_id_for(document_id, ordinal, body),
                    document_id=document_id,
                    ordinal=ordinal,
                    text=body,
                    start_char=start,
                    end_char=end,
                    article=article,
                    section=_section_at(sections, start),
                )
            )
            ordinal += 1

    return chunks
