from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.config import Settings
from app.ingestion import read_path
from app.store import DocumentStore

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS = REPO_ROOT / "data" / "corpus"
EVAL = REPO_ROOT / "data" / "eval"


@pytest.fixture
def corpus_dir() -> Path:
    return CORPUS


@pytest.fixture
def lei_text() -> str:
    return read_path(CORPUS / "lei-4444-2021.txt")


@pytest.fixture
def portaria_text() -> str:
    return read_path(CORPUS / "portaria-45-2024.txt")


def build_minimal_pdf(text: str) -> bytes:
    """PDF válido mínimo (sem dependência extra) para testar a extração real."""
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    body = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
        b"4 0 obj\n<< /Length "
        + str(len(content)).encode()
        + b" >>\nstream\n"
        + content
        + b"\nendstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    out = b"%PDF-1.4\n"
    offsets: list[int] = []
    for chunk in body:
        offsets.append(len(out))
        out += chunk
    xref = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n" + b"".join(
        f"{offset:010d} 00000 n \n".encode() for offset in offsets
    )
    out += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF\n"
    return out


@pytest.fixture
def minimal_pdf() -> bytes:
    return build_minimal_pdf("Art. 1o Documento de teste.")


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Settings isoladas: copia o corpus e o golden set para um tmpdir."""
    data_dir = tmp_path / "data"
    shutil.copytree(CORPUS, data_dir / "corpus")
    shutil.copytree(EVAL, data_dir / "eval")
    monkeypatch.setenv("LEXIA_DATA_DIR", str(data_dir))
    monkeypatch.delenv("LEXIA_EXTRACTOR", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    created = Settings()
    created.ensure_dirs()
    return created


@pytest.fixture
def store(settings: Settings) -> DocumentStore:
    built = DocumentStore(chunk_max_chars=settings.chunk_max_chars, chunk_overlap=settings.chunk_overlap)
    for path in sorted(settings.corpus_dir.glob("*.txt")):
        built.add_document(text=read_path(path), source=path.name)
    return built
