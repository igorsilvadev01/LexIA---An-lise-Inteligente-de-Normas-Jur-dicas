import pytest

from app.config import Settings
from app.evaluation.metrics import (
    ConfusionAccumulator,
    greedy_match,
    mean_reciprocal_rank,
    prf,
    recall_at_k,
    scalar_match,
    token_set_similarity,
)
from app.evaluation.runner import (
    evaluate_extraction,
    evaluate_retrieval,
    load_golden,
    load_queries,
    render_markdown,
)
from app.extraction.service import ExtractionService
from app.models import Deadline, LegalNorm, Obligation
from app.store import DocumentStore


def test_prf_casos_de_borda():
    assert prf(0, 0, 0) == (1.0, 1.0, 1.0)
    assert prf(0, 2, 0)[0] == 0.0
    assert prf(1, 2, 2) == (0.5, 0.5, 0.5)


def test_token_set_similarity():
    assert token_set_similarity("prazo de 15 dias", "prazo de 15 dias") == 1.0
    assert token_set_similarity("prazo", "multa") == 0.0
    assert 0 < token_set_similarity("prazo de 15 dias", "prazo de 30 dias") < 1


def test_greedy_match_pareia_um_para_um():
    pred = ["a", "a"]
    gold = ["a"]
    assert greedy_match(pred, gold, lambda p, g: float(p == g), 1.0) == 1


def test_scalar_match_abstencao_nao_conta_como_erro():
    assert scalar_match("number", None, None) == (0, 0, 0)
    assert scalar_match("number", "1", None) == (0, 1, 0)  # alucinação = falso positivo
    assert scalar_match("number", None, "1") == (0, 0, 1)  # omissão = falso negativo


def test_scalar_match_subject_usa_similaridade():
    assert scalar_match("subject", "Dispõe sobre dados pessoais.", "Dispõe sobre dados pessoais")[0] == 1
    assert scalar_match("subject", "Trata de licitações", "Dispõe sobre dados pessoais")[0] == 0


def test_accumulator_extracao_perfeita_da_f1_um():
    norm = LegalNorm(
        norm_type="lei",
        number="1",
        obligations=[Obligation(action="publicar relatório", article="Art. 1º", evidence="x")],
        deadlines=[Deadline(description="prazo", value=5, unit="dias", article="Art. 1º")],
    )
    acc = ConfusionAccumulator()
    acc.add_norm(norm, norm)
    assert acc.macro_f1() == 1.0 and acc.micro_f1() == 1.0


def test_accumulator_penaliza_artigo_errado():
    gold = LegalNorm(deadlines=[Deadline(description="prazo", value=5, unit="dias", article="Art. 1º")])
    pred = LegalNorm(deadlines=[Deadline(description="prazo", value=5, unit="dias", article="Art. 9º")])
    acc = ConfusionAccumulator()
    acc.add_norm(pred, gold)
    scores = {s.field: s.f1 for s in acc.field_scores()}
    assert scores["deadlines"] == 0.0


def test_metricas_de_recuperacao():
    assert recall_at_k(["a", "b"], {"b"}, 2) == 1.0
    assert recall_at_k(["a", "b"], {"b"}, 1) == 0.0
    assert recall_at_k([], set(), 3) == 0.0
    assert mean_reciprocal_rank(["a", "b"], {"b"}) == 0.5
    assert mean_reciprocal_rank(["a"], {"z"}) == 0.0


def test_golden_set_valida_contra_o_schema(settings: Settings):
    golden = load_golden(settings.eval_dir / "golden.json")
    assert len(golden) == 5
    assert golden["lei-4444-2021.txt"].number == "4.444"


def test_avaliacao_de_extracao_ponta_a_ponta(store: DocumentStore, settings: Settings):
    golden = load_golden(settings.eval_dir / "golden.json")
    report, por_documento = evaluate_extraction(store, ExtractionService(settings), golden)
    assert report.n_documents == 5
    assert report.backend == "rules"
    assert 0.9 <= report.macro_f1 <= 1.0  # baseline medido: ~0.97
    campos = {s.field: s for s in report.field_scores}
    assert campos["publication_date"].f1 == 1.0
    assert campos["obligations"].recall < 1.0  # limitação conhecida do baseline
    pior = min(por_documento, key=lambda d: d["macro_f1"])
    assert pior["source"] == "portaria-45-2024.txt"


def test_avaliacao_de_recuperacao(store: DocumentStore, settings: Settings):
    metricas = evaluate_retrieval(store, load_queries(settings.eval_dir / "retrieval.json"), top_k=5)
    assert metricas["recall@5"] >= 0.9
    assert metricas["mrr"] >= 0.8
    assert metricas["queries"] == 12


def test_render_markdown_contem_tabelas(store: DocumentStore, settings: Settings):
    golden = load_golden(settings.eval_dir / "golden.json")
    report, por_documento = evaluate_extraction(store, ExtractionService(settings), golden)
    report.retrieval = evaluate_retrieval(store, load_queries(settings.eval_dir / "retrieval.json"), top_k=5)
    markdown = render_markdown(report, por_documento)
    assert "## Métricas por campo" in markdown
    assert "## Recuperação" in markdown
    assert "`obligations`" in markdown


@pytest.mark.parametrize("campo", ["norm_type", "number", "year", "issuing_body", "subject"])
def test_campos_de_cabecalho_tem_f1_perfeito_no_corpus(store: DocumentStore, settings: Settings, campo: str):
    golden = load_golden(settings.eval_dir / "golden.json")
    report, _ = evaluate_extraction(store, ExtractionService(settings), golden)
    assert {s.field: s.f1 for s in report.field_scores}[campo] == 1.0
