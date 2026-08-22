"""Repositório de documentos + índices, com persistência em JSON.

O estado canônico são os documentos; os índices são derivados e reconstruídos
no carregamento. Isso evita serializar matrizes e mantém o formato do arquivo
legível/diffável.
"""

from __future__ import annotations

import json
from pathlib import Path

from .chunking import chunk_text
from .index import Bm25Index, TfidfIndex
from .ingestion import document_id_for, guess_title
from .models import Chunk, Document, SearchHit
from .retrieval import reciprocal_rank_fusion
from .text import normalize_whitespace


class DocumentStore:
    """Armazena documentos/chunks e responde buscas híbridas."""

    def __init__(self, *, chunk_max_chars: int = 1200, chunk_overlap: int = 120) -> None:
        self.chunk_max_chars = chunk_max_chars
        self.chunk_overlap = chunk_overlap
        self.documents: dict[str, Document] = {}
        self.chunks: dict[str, Chunk] = {}
        self._lexical = Bm25Index()
        self._semantic = TfidfIndex()

    # ------------------------------------------------------------------ escrita
    def add_document(
        self,
        *,
        text: str,
        source: str,
        title: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> Document:
        """Ingere um documento. Reingerir o mesmo conteúdo é idempotente."""
        normalized = normalize_whitespace(text)
        if not normalized:
            raise ValueError("texto vazio")
        doc_id = document_id_for(source, normalized)
        if doc_id in self.documents:
            return self.documents[doc_id]

        chunks = chunk_text(
            normalized,
            doc_id,
            max_chars=self.chunk_max_chars,
            overlap=self.chunk_overlap,
        )
        document = Document(
            id=doc_id,
            title=title or guess_title(normalized, source),
            source=source,
            text=normalized,
            n_chunks=len(chunks),
            metadata=metadata or {},
        )
        self.documents[doc_id] = document
        for chunk in chunks:
            self.chunks[chunk.id] = chunk
            self._lexical.add(chunk.id, chunk.text)
            self._semantic.add(chunk.id, chunk.text)
        self._semantic.build()
        return document

    def delete_document(self, document_id: str) -> bool:
        if document_id not in self.documents:
            return False
        del self.documents[document_id]
        self.chunks = {cid: c for cid, c in self.chunks.items() if c.document_id != document_id}
        self._reindex()
        return True

    def _reindex(self) -> None:
        self._lexical = Bm25Index()
        self._semantic = TfidfIndex()
        for chunk in sorted(self.chunks.values(), key=lambda c: (c.document_id, c.ordinal)):
            self._lexical.add(chunk.id, chunk.text)
            self._semantic.add(chunk.id, chunk.text)
        self._semantic.build()

    # ------------------------------------------------------------------ leitura
    def get_document(self, document_id: str) -> Document | None:
        return self.documents.get(document_id)

    def chunks_of(self, document_id: str) -> list[Chunk]:
        return sorted(
            (c for c in self.chunks.values() if c.document_id == document_id),
            key=lambda c: c.ordinal,
        )

    def search(self, query: str, *, top_k: int = 5, document_id: str | None = None) -> list[SearchHit]:
        """Busca híbrida (BM25 + TF-IDF) fundida por RRF."""
        if not query.strip() or not self.chunks:
            return []
        pool = max(top_k * 4, 20)
        allowed = (
            {c.id for c in self.chunks.values() if c.document_id == document_id} if document_id else None
        )
        if allowed is not None and not allowed:
            return []
        lexical = self._lexical.search(query, top_k=pool, allowed_ids=allowed)
        semantic = self._semantic.search(query, top_k=pool, allowed_ids=allowed)
        fused = reciprocal_rank_fusion(
            {"lexical": lexical, "semantic": semantic},
            weights={"lexical": 1.0, "semantic": 1.0},
        )

        hits: list[SearchHit] = []
        for item in fused:
            chunk = self.chunks.get(item.id)
            if chunk is None:
                continue
            if document_id and chunk.document_id != document_id:
                continue
            document = self.documents.get(chunk.document_id)
            hits.append(
                SearchHit(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_title=document.title if document else chunk.document_id,
                    text=chunk.text,
                    score=round(item.score, 6),
                    lexical_score=round(item.lexical_score, 6),
                    semantic_score=round(item.semantic_score, 6),
                    article=chunk.article,
                )
            )
            if len(hits) >= top_k:
                break
        return hits

    def stats(self) -> dict[str, int]:
        return {
            "documents": len(self.documents),
            "chunks": len(self.chunks),
            "vocab_size": self._semantic.vocab_size,
            "characters": sum(len(d.text) for d in self.documents.values()),
        }

    # -------------------------------------------------------------- persistência
    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chunk_max_chars": self.chunk_max_chars,
            "chunk_overlap": self.chunk_overlap,
            "documents": [json.loads(d.model_dump_json()) for d in self.documents.values()],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> DocumentStore:
        if not path.exists():
            return cls()
        payload = json.loads(path.read_text(encoding="utf-8"))
        store = cls(
            chunk_max_chars=payload.get("chunk_max_chars", 1200),
            chunk_overlap=payload.get("chunk_overlap", 120),
        )
        for raw in payload.get("documents", []):
            store.add_document(
                text=raw["text"],
                source=raw["source"],
                title=raw.get("title"),
                metadata=raw.get("metadata") or {},
            )
        return store
