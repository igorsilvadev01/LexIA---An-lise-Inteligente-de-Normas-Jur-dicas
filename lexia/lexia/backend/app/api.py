"""API HTTP (FastAPI) do LexIA."""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import __version__
from .config import Settings, get_settings
from .extraction.service import ExtractionService
from .ingestion import UnsupportedDocumentError, iter_corpus, read_bytes, read_path
from .models import Chunk, Document, ExtractionResult, SearchHit
from .store import DocumentStore

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class TextIngestRequest(BaseModel):
    text: str = Field(min_length=20, description="Conteúdo do documento")
    title: str | None = None
    source: str = Field(default="entrada-manual.txt")


class SearchRequest(BaseModel):
    query: str = Field(min_length=2)
    top_k: int = Field(default=5, ge=1, le=50)
    document_id: str | None = None


class DocumentSummary(BaseModel):
    id: str
    title: str
    source: str
    n_chunks: int
    n_chars: int


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]


class EvaluationResponse(BaseModel):
    report: dict
    per_document: list[dict]
    markdown: str


def _summary(document: Document) -> DocumentSummary:
    return DocumentSummary(
        id=document.id,
        title=document.title,
        source=document.source,
        n_chunks=document.n_chunks,
        n_chars=len(document.text),
    )


def create_app(settings: Settings | None = None, *, store: DocumentStore | None = None) -> FastAPI:
    """Cria a aplicação. Injetar `settings`/`store` mantém os testes isolados."""
    settings = settings or get_settings()
    settings.ensure_dirs()

    state_store = store or (
        DocumentStore.load(settings.index_path)
        if settings.persist
        else DocumentStore(
            chunk_max_chars=settings.chunk_max_chars,
            chunk_overlap=settings.chunk_overlap,
        )
    )
    extraction_service = ExtractionService(settings)
    extraction_cache: dict[str, ExtractionResult] = {}

    app = FastAPI(
        title="LexIA API",
        version=__version__,
        description=("Ingestão, indexação, busca híbrida e extração estruturada de normas jurídicas."),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_store() -> DocumentStore:
        return state_store

    def persist() -> None:
        if settings.persist:
            state_store.save(settings.index_path)

    @app.get("/api/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "version": __version__,
            "extractor_backend": extraction_service.backend,
        }

    @app.get("/api/stats", tags=["meta"])
    def stats(store: DocumentStore = Depends(get_store)) -> dict[str, int | str]:
        return {**store.stats(), "extractor_backend": extraction_service.backend}

    @app.get("/api/documents", response_model=list[DocumentSummary], tags=["documentos"])
    def list_documents(store: DocumentStore = Depends(get_store)) -> list[DocumentSummary]:
        return [_summary(doc) for doc in store.documents.values()]

    @app.post("/api/documents/text", response_model=DocumentSummary, status_code=201, tags=["documentos"])
    def ingest_text(payload: TextIngestRequest, store: DocumentStore = Depends(get_store)) -> DocumentSummary:
        try:
            document = store.add_document(text=payload.text, source=payload.source, title=payload.title)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        persist()
        return _summary(document)

    @app.post("/api/documents/upload", response_model=DocumentSummary, status_code=201, tags=["documentos"])
    async def upload_document(
        file: UploadFile = File(...), store: DocumentStore = Depends(get_store)
    ) -> DocumentSummary:
        payload = await file.read()
        if len(payload) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="arquivo maior que 10 MB")
        try:
            text = read_bytes(file.filename or "upload.txt", payload)
        except UnsupportedDocumentError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc
        document = store.add_document(text=text, source=file.filename or "upload.txt")
        persist()
        return _summary(document)

    @app.post("/api/corpus/load", tags=["documentos"])
    def load_corpus(store: DocumentStore = Depends(get_store)) -> dict[str, int]:
        """Ingere (idempotentemente) todos os arquivos de `data/corpus`."""
        loaded = 0
        for path in iter_corpus(settings.corpus_dir):
            before = len(store.documents)
            store.add_document(text=read_path(path), source=path.name)
            loaded += len(store.documents) - before
        persist()
        return {"loaded": loaded, **store.stats()}

    @app.get("/api/documents/{document_id}", tags=["documentos"])
    def get_document(document_id: str, store: DocumentStore = Depends(get_store)) -> Document:
        document = store.get_document(document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="documento não encontrado")
        return document

    @app.get("/api/documents/{document_id}/chunks", response_model=list[Chunk], tags=["documentos"])
    def get_chunks(document_id: str, store: DocumentStore = Depends(get_store)) -> list[Chunk]:
        if store.get_document(document_id) is None:
            raise HTTPException(status_code=404, detail="documento não encontrado")
        return store.chunks_of(document_id)

    @app.delete("/api/documents/{document_id}", status_code=204, tags=["documentos"])
    def delete_document(document_id: str, store: DocumentStore = Depends(get_store)) -> None:
        if not store.delete_document(document_id):
            raise HTTPException(status_code=404, detail="documento não encontrado")
        extraction_cache.pop(document_id, None)
        persist()

    @app.post("/api/search", response_model=SearchResponse, tags=["busca"])
    def search(payload: SearchRequest, store: DocumentStore = Depends(get_store)) -> SearchResponse:
        hits = store.search(payload.query, top_k=payload.top_k, document_id=payload.document_id)
        return SearchResponse(query=payload.query, hits=hits)

    @app.post("/api/documents/{document_id}/extract", response_model=ExtractionResult, tags=["extração"])
    def extract(
        document_id: str, refresh: bool = False, store: DocumentStore = Depends(get_store)
    ) -> ExtractionResult:
        document = store.get_document(document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="documento não encontrado")
        if refresh or document_id not in extraction_cache:
            extraction_cache[document_id] = extraction_service.extract(
                document_id=document_id, text=document.text
            )
        return extraction_cache[document_id]

    @app.post("/api/evaluate", response_model=EvaluationResponse, tags=["avaliação"])
    def evaluate(store: DocumentStore = Depends(get_store)) -> EvaluationResponse:
        from .evaluation.runner import (
            evaluate_extraction,
            evaluate_retrieval,
            load_golden,
            load_queries,
            render_markdown,
        )

        golden_path = settings.eval_dir / "golden.json"
        if not golden_path.exists():
            raise HTTPException(status_code=404, detail="golden set não encontrado")
        report, per_document = evaluate_extraction(store, extraction_service, load_golden(golden_path))
        queries_path = settings.eval_dir / "retrieval.json"
        if queries_path.exists():
            report.retrieval = evaluate_retrieval(store, load_queries(queries_path), top_k=settings.top_k)
        return EvaluationResponse(
            report=report.model_dump(mode="json"),
            per_document=per_document,
            markdown=render_markdown(report, per_document),
        )

    return app


app = create_app()


def corpus_files() -> list[Path]:  # pragma: no cover - utilitário de conveniência
    return list(iter_corpus(get_settings().corpus_dir))
