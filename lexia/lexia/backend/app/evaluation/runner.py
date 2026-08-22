"""Execução da avaliação ponta a ponta (extração + recuperação) e relatório."""

from __future__ import annotations

import json
from pathlib import Path

from ..extraction.service import ExtractionService
from ..models import EvalReport, LegalNorm
from ..store import DocumentStore
from .metrics import ConfusionAccumulator, mean_reciprocal_rank, recall_at_k


def load_golden(path: Path) -> dict[str, LegalNorm]:
    """Carrega o golden set anotado à mão, validando-o contra o schema."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {entry["source"]: LegalNorm.model_validate(entry["norm"]) for entry in payload["documents"]}


def load_queries(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["queries"]


def evaluate_extraction(
    store: DocumentStore,
    service: ExtractionService,
    golden: dict[str, LegalNorm],
) -> tuple[EvalReport, list[dict]]:
    """Compara a extração de cada documento com o golden set.

    Devolve o relatório agregado e os detalhes por documento (útil para depurar
    qual documento puxou a métrica para baixo).
    """
    accumulator = ConfusionAccumulator()
    per_document: list[dict] = []
    evaluated = 0
    backend = service.backend

    for document in store.documents.values():
        gold = golden.get(Path(document.source).name)
        if gold is None:
            continue
        result = service.extract(document_id=document.id, text=document.text)
        local = ConfusionAccumulator()
        local.add_norm(result.norm, gold)
        accumulator.add_norm(result.norm, gold)
        evaluated += 1
        per_document.append(
            {
                "source": Path(document.source).name,
                "macro_f1": local.macro_f1(),
                "micro_f1": local.micro_f1(),
                "latency_ms": result.latency_ms,
                "warnings": result.warnings,
                "weakest_fields": [
                    score.field
                    for score in sorted(local.field_scores(), key=lambda s: s.f1)[:3]
                    if score.f1 < 1.0
                ],
            }
        )

    report = EvalReport(
        backend=backend,
        prompt_version=service.settings.prompt_version if backend == "llm" else None,
        n_documents=evaluated,
        field_scores=accumulator.field_scores(),
        macro_f1=accumulator.macro_f1(),
        micro_f1=accumulator.micro_f1(),
    )
    return report, per_document


def evaluate_retrieval(store: DocumentStore, queries: list[dict], *, top_k: int = 5) -> dict[str, float]:
    """Métricas de recuperação: Recall@1, Recall@k, MRR e cobertura."""
    source_by_id = {doc.id: Path(doc.source).name for doc in store.documents.values()}
    recalls_1: list[float] = []
    recalls_k: list[float] = []
    mrrs: list[float] = []

    for item in queries:
        relevant = {f"{source}::{article}" for source, article in item["relevant"]}
        hits = store.search(item["query"], top_k=top_k)
        retrieved = [f"{source_by_id.get(hit.document_id, hit.document_id)}::{hit.article}" for hit in hits]
        recalls_1.append(recall_at_k(retrieved, relevant, 1))
        recalls_k.append(recall_at_k(retrieved, relevant, top_k))
        mrrs.append(mean_reciprocal_rank(retrieved, relevant))

    n = max(1, len(queries))
    return {
        "queries": float(len(queries)),
        "top_k": float(top_k),
        "recall@1": round(sum(recalls_1) / n, 4),
        f"recall@{top_k}": round(sum(recalls_k) / n, 4),
        "mrr": round(sum(mrrs) / n, 4),
    }


def render_markdown(report: EvalReport, per_document: list[dict]) -> str:
    """Relatório legível (usado em docs/EVALUATION.md e na saída do CLI)."""
    lines = [
        "# Relatório de avaliação — LexIA",
        "",
        f"- Backend de extração: **{report.backend}**"
        + (f" (prompt `{report.prompt_version}`)" if report.prompt_version else ""),
        f"- Documentos avaliados: **{report.n_documents}**",
        f"- Macro-F1: **{report.macro_f1:.3f}** · Micro-F1: **{report.micro_f1:.3f}**",
        f"- Gerado em: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "## Métricas por campo",
        "",
        "| Campo | Precisão | Revocação | F1 | Itens no golden | Itens previstos |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for score in report.field_scores:
        lines.append(
            f"| `{score.field}` | {score.precision:.3f} | {score.recall:.3f} | "
            f"{score.f1:.3f} | {score.support} | {score.predicted} |"
        )

    if report.retrieval:
        lines += ["", "## Recuperação", "", "| Métrica | Valor |", "| --- | --- |"]
        for key, value in report.retrieval.items():
            lines.append(f"| {key} | {value:g} |")

    lines += [
        "",
        "## Por documento",
        "",
        "| Documento | Macro-F1 | Campos mais fracos |",
        "| --- | --- | --- |",
    ]
    for item in sorted(per_document, key=lambda d: d["macro_f1"]):
        weakest = ", ".join(f"`{f}`" for f in item["weakest_fields"]) or "—"
        lines.append(f"| {item['source']} | {item['macro_f1']:.3f} | {weakest} |")

    return "\n".join(lines) + "\n"
