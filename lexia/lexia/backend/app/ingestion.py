"""Ingestão de documentos: leitura de arquivos, normalização e chunking."""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

from .text import normalize_whitespace

SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf"}


class UnsupportedDocumentError(ValueError):
    """Arquivo com extensão/conteúdo não suportado."""


def document_id_for(source: str, text: str) -> str:
    """Id determinístico: mesma origem + mesmo conteúdo => mesmo id (idempotência)."""
    digest = hashlib.sha1(f"{source}\n{text}".encode()).hexdigest()[:12]
    slug = re.sub(r"[^a-z0-9]+", "-", Path(source).stem.lower()).strip("-") or "doc"
    return f"{slug[:40]}-{digest}"


def extract_pdf_text(payload: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(payload))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def read_bytes(filename: str, payload: bytes) -> str:
    """Converte bytes de upload em texto normalizado."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise UnsupportedDocumentError(
            f"extensão '{suffix or '(nenhuma)'}' não suportada; use {sorted(SUPPORTED_SUFFIXES)}"
        )
    raw = extract_pdf_text(payload) if suffix == ".pdf" else payload.decode("utf-8", errors="replace")
    text = normalize_whitespace(raw)
    if not text:
        raise UnsupportedDocumentError("documento vazio após normalização")
    return text


def read_path(path: Path) -> str:
    return read_bytes(path.name, path.read_bytes())


def guess_title(text: str, fallback: str) -> str:
    """Título = primeira linha não vazia com aparência de cabeçalho."""
    for line in text.split("\n"):
        stripped = line.strip()
        if len(stripped) >= 8 and not stripped.lower().startswith("art"):
            return stripped[:160]
    return fallback


def iter_corpus(directory: Path):
    """Itera arquivos suportados de um diretório, em ordem estável."""
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            yield path
