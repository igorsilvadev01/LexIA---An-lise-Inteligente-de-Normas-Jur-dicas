from app.index import Bm25Index, TfidfIndex
from app.retrieval import reciprocal_rank_fusion


def _povoar(index):
    index.add("a", "O prazo para responder o pedido do titular é de 15 dias.")
    index.add("b", "A multa poderá chegar a R$ 50.000.000,00 por infração.")
    index.add("c", "O relatório de transparência algorítmica é semestral.")
    return index


def test_bm25_ranqueia_documento_mais_relevante():
    index = _povoar(Bm25Index())
    assert index.search("prazo do titular")[0][0] == "a"
    assert index.search("multa por infração")[0][0] == "b"


def test_bm25_ignora_consulta_sem_termos_uteis():
    index = _povoar(Bm25Index())
    assert index.search("de a o") == []


def test_bm25_vazio():
    assert Bm25Index().search("qualquer") == []


def test_bm25_respeita_top_k():
    index = _povoar(Bm25Index())
    assert len(index.search("prazo multa relatório", top_k=2)) <= 2


def test_tfidf_cosseno_em_zero_um():
    index = _povoar(TfidfIndex())
    index.build()
    resultados = index.search("relatório de transparência")
    assert resultados[0][0] == "c"
    assert all(0.0 < score <= 1.0001 for _, score in resultados)


def test_tfidf_termo_desconhecido_nao_retorna_nada():
    index = _povoar(TfidfIndex())
    index.build()
    assert index.search("blockchain") == []


def test_tfidf_reconstroi_apos_novo_documento():
    index = _povoar(TfidfIndex())
    index.build()
    tamanho_inicial = index.vocab_size
    index.add("d", "Vedação de compartilhamento com terceiros.")
    assert index.search("vedação")[0][0] == "d"
    assert index.vocab_size > tamanho_inicial


def test_rrf_prioriza_consenso_entre_rankings():
    fundido = reciprocal_rank_fusion(
        {
            "lexical": [("x", 9.0), ("y", 8.0), ("z", 1.0)],
            "semantic": [("y", 0.9), ("x", 0.2)],
        }
    )
    assert [hit.id for hit in fundido][:2] == ["x", "y"]
    assert fundido[0].lexical_score == 9.0
    assert fundido[1].semantic_score == 0.9


def test_rrf_aplica_pesos():
    fundido = reciprocal_rank_fusion(
        {"lexical": [("x", 1.0)], "semantic": [("y", 1.0)]},
        weights={"lexical": 0.1, "semantic": 5.0},
    )
    assert fundido[0].id == "y"


def test_rrf_sem_entradas():
    assert reciprocal_rank_fusion({}) == []
