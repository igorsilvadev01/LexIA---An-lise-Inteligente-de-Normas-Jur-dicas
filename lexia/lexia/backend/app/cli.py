"""CLI do LexIA: `python -m app.cli <comando>`.

Comandos:
    ingest    ingere os arquivos de data/corpus (ou um caminho informado)
    search    busca híbrida na base indexada
    extract   extração estruturada de um documento
    eval      roda a avaliação e escreve docs/EVALUATION.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import get_settings
from .evaluation.runner import (
    evaluate_extraction,
    evaluate_retrieval,
    load_golden,
    load_queries,
    render_markdown,
)
from .extraction.service import ExtractionService
from .ingestion import iter_corpus, read_path
from .store import DocumentStore


def _load_store(rebuild: bool = False) -> DocumentStore:
    settings = get_settings()
    settings.ensure_dirs()
    if not rebuild and settings.index_path.exists():
        return DocumentStore.load(settings.index_path)
    store = DocumentStore(chunk_max_chars=settings.chunk_max_chars, chunk_overlap=settings.chunk_overlap)
    for path in iter_corpus(settings.corpus_dir):
        store.add_document(text=read_path(path), source=path.name)
    store.save(settings.index_path)
    return store


def cmd_ingest(args: argparse.Namespace) -> int:
    settings = get_settings()
    settings.ensure_dirs()
    store = DocumentStore(chunk_max_chars=settings.chunk_max_chars, chunk_overlap=settings.chunk_overlap)
    paths = [Path(args.path)] if args.path else list(iter_corpus(settings.corpus_dir))
    for path in paths:
        document = store.add_document(text=read_path(path), source=path.name)
        print(f"[ok] {path.name} -> {document.id} ({document.n_chunks} chunks)")
    store.save(settings.index_path)
    print(json.dumps(store.stats(), indent=2, ensure_ascii=False))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    store = _load_store()
    hits = store.search(args.query, top_k=args.top_k)
    if not hits:
        print("nenhum resultado")
        return 0
    for position, hit in enumerate(hits, start=1):
        snippet = " ".join(hit.text.split())[:220]
        print(f"\n#{position} score={hit.score:.4f} {hit.document_title} [{hit.article or '-'}]")
        print(f"    {snippet}")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    store = _load_store()
    document = store.get_document(args.document_id) or next(
        (d for d in store.documents.values() if args.document_id in d.source), None
    )
    if document is None:
        print(f"documento '{args.document_id}' não encontrado", file=sys.stderr)
        return 1
    result = ExtractionService().extract(document_id=document.id, text=document.text)
    print(result.model_dump_json(indent=2))
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    settings = get_settings()
    store = _load_store(rebuild=True)
    service = ExtractionService(settings)
    report, per_document = evaluate_extraction(store, service, load_golden(settings.eval_dir / "golden.json"))
    queries_path = settings.eval_dir / "retrieval.json"
    if queries_path.exists():
        report.retrieval = evaluate_retrieval(store, load_queries(queries_path), top_k=settings.top_k)
    markdown = render_markdown(report, per_document)
    print(markdown)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown, encoding="utf-8")
        print(f"[ok] relatório escrito em {out}")
    if args.min_macro_f1 is not None and report.macro_f1 < args.min_macro_f1:
        print(
            f"[falha] macro-F1 {report.macro_f1:.3f} abaixo do mínimo {args.min_macro_f1:.3f}",
            file=sys.stderr,
        )
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lexia", description="LexIA — pipeline jurídico com IA")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="ingere documentos e grava o índice")
    ingest.add_argument("--path", help="arquivo específico (padrão: data/corpus)")
    ingest.set_defaults(func=cmd_ingest)

    search = sub.add_parser("search", help="busca híbrida")
    search.add_argument("query")
    search.add_argument("--top-k", type=int, default=5)
    search.set_defaults(func=cmd_search)

    extract = sub.add_parser("extract", help="extração estruturada")
    extract.add_argument("document_id", help="id do documento ou parte do nome do arquivo")
    extract.set_defaults(func=cmd_extract)

    evaluate = sub.add_parser("eval", help="roda a avaliação contra o golden set")
    evaluate.add_argument("--out", help="caminho do relatório markdown")
    evaluate.add_argument("--min-macro-f1", type=float, help="falha se o macro-F1 ficar abaixo")
    evaluate.set_defaults(func=cmd_eval)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
