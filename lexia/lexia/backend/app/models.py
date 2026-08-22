"""Modelos de domínio (Pydantic) compartilhados entre pipeline e API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

NormType = Literal[
    "lei",
    "decreto",
    "resolucao",
    "portaria",
    "instrucao_normativa",
    "medida_provisoria",
    "desconhecido",
]


class Chunk(BaseModel):
    """Trecho indexável de um documento, com metadados de rastreabilidade."""

    id: str
    document_id: str
    ordinal: int = Field(ge=0, description="Posição do chunk dentro do documento")
    text: str
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)
    article: str | None = Field(default=None, description="Ex.: 'Art. 5º' quando detectado")
    section: str | None = None

    @property
    def n_chars(self) -> int:
        return len(self.text)


class Document(BaseModel):
    """Documento normativo ingerido."""

    id: str
    title: str
    source: str
    text: str
    n_chunks: int = 0
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, str] = Field(default_factory=dict)


class SearchHit(BaseModel):
    """Resultado de busca com pontuações por estratégia (auditável)."""

    chunk_id: str
    document_id: str
    document_title: str
    text: str
    score: float
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    article: str | None = None


class Obligation(BaseModel):
    """Obrigação normativa extraída."""

    actor: str | None = Field(default=None, description="Quem é obrigado")
    action: str = Field(description="O que deve ser feito")
    article: str | None = None
    evidence: str = Field(description="Trecho literal que fundamenta a extração")


class Deadline(BaseModel):
    """Prazo previsto na norma."""

    description: str
    value: int | None = None
    unit: Literal["dias", "meses", "anos", "horas", "indefinido"] = "indefinido"
    article: str | None = None
    evidence: str = ""


class Penalty(BaseModel):
    """Penalidade/sanção prevista na norma."""

    description: str
    kind: Literal["multa", "advertencia", "suspensao", "cassacao", "outra"] = "outra"
    amount: str | None = None
    article: str | None = None
    evidence: str = ""


class LegalNorm(BaseModel):
    """Schema alvo da extração estruturada.

    É o contrato usado tanto pelo extrator determinístico (regras) quanto pelo
    extrator baseado em LLM — o que permite comparar os dois na avaliação.
    """

    norm_type: NormType = "desconhecido"
    number: str | None = None
    year: int | None = None
    issuing_body: str | None = None
    publication_date: str | None = Field(default=None, description="ISO-8601 (YYYY-MM-DD)")
    effective_date: str | None = Field(default=None, description="ISO-8601 (YYYY-MM-DD)")
    subject: str | None = Field(default=None, description="Ementa/objeto em uma frase")
    obligations: list[Obligation] = Field(default_factory=list)
    deadlines: list[Deadline] = Field(default_factory=list)
    penalties: list[Penalty] = Field(default_factory=list)
    references: list[str] = Field(
        default_factory=list, description="Normas citadas, ex.: 'Lei nº 13.709/2018'"
    )


class ExtractionResult(BaseModel):
    """Extração + proveniência (qual backend/prompt gerou o resultado)."""

    document_id: str
    norm: LegalNorm
    backend: Literal["rules", "llm"]
    prompt_version: str | None = None
    model: str | None = None
    latency_ms: float = 0.0
    warnings: list[str] = Field(default_factory=list)


class FieldScore(BaseModel):
    """Métrica de um campo do schema."""

    field: str
    precision: float
    recall: float
    f1: float
    support: int
    predicted: int


class EvalReport(BaseModel):
    """Relatório agregado da avaliação."""

    backend: str
    prompt_version: str | None
    n_documents: int
    field_scores: list[FieldScore]
    macro_f1: float
    micro_f1: float
    retrieval: dict[str, float] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
