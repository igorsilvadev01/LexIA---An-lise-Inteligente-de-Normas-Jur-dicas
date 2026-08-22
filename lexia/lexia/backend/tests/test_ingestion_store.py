from pathlib import Path

import pytest

from app.config import Settings
from app.ingestion import (
    UnsupportedDocumentError,
    document_id_for,
    guess_title,
    iter_corpus,
    read_bytes,
)
from app.store import DocumentStore


def test_read_bytes_txt_normaliza():
    assert read_bytes("a.txt", "  Art.  1º   teste  ".encode()) == "Art. 1º teste"


def test_read_bytes_pdf_extrai_texto(minimal_pdf: bytes):
    assert "Documento de teste" in read_bytes("a.pdf", minimal_pdf)


def test_read_bytes_extensao_nao_suportada():
    with pytest.raises(UnsupportedDocumentError):
        read_bytes("planilha.xlsx", b"conteudo")


def test_read_bytes_documento_vazio():
    with pytest.raises(UnsupportedDocumentError):
        read_bytes("a.txt", b"   \n  ")


def test_document_id_determinístico_e_sensivel_ao_conteudo():
    assert document_id_for("lei.txt", "texto") == document_id_for("lei.txt", "texto")
    assert document_id_for("lei.txt", "texto") != document_id_for("lei.txt", "outro")


def test_guess_title_usa_primeira_linha_relevante():
    assert guess_title("\nPRESIDÊNCIA DA REPÚBLICA\nArt. 1º ...", "fallback") == ("PRESIDÊNCIA DA REPÚBLICA")
    assert guess_title("curto", "fallback") == "fallback"


def test_iter_corpus_ordem_estavel(corpus_dir: Path):
    nomes = [p.name for p in iter_corpus(corpus_dir)]
    assert nomes == sorted(nomes) and len(nomes) == 5


def test_store_ingestao_idempotente(lei_text: str):
    store = DocumentStore()
    primeiro = store.add_document(text=lei_text, source="lei.txt")
    segundo = store.add_document(text=lei_text, source="lei.txt")
    assert primeiro.id == segundo.id
    assert store.stats()["documents"] == 1


def test_store_rejeita_texto_vazio():
    with pytest.raises(ValueError):
        DocumentStore().add_document(text="   ", source="x.txt")


def test_store_busca_encontra_artigo_correto(store: DocumentStore):
    hits = store.search("prazo para responder pedido de acesso do titular", top_k=3)
    assert hits[0].article == "Art. 4º"
    assert "lei-4444" in hits[0].document_id
    assert hits[0].score > 0


def test_store_busca_pode_filtrar_por_documento(store: DocumentStore):
    alvo = next(d for d in store.documents.values() if "portaria" in d.source)
    hits = store.search("inventário de ativos de informação", top_k=5, document_id=alvo.id)
    assert hits and all(hit.document_id == alvo.id for hit in hits)
    # sem o filtro, o mesmo trecho continua recuperável
    assert any(
        hit.document_id == alvo.id for hit in store.search("inventário de ativos de informação", top_k=5)
    )


def test_store_busca_sem_resultado_para_consulta_vazia(store: DocumentStore):
    assert store.search("   ") == []


def test_store_remove_documento_e_reindexa(store: DocumentStore):
    alvo = next(d for d in store.documents.values() if "resolucao" in d.source)
    assert store.delete_document(alvo.id) is True
    assert store.delete_document(alvo.id) is False
    assert alvo.id not in store.documents
    assert all(hit.document_id != alvo.id for hit in store.search("transparência algorítmica"))


def test_store_persistencia_roundtrip(store: DocumentStore, settings: Settings):
    store.save(settings.index_path)
    recarregado = DocumentStore.load(settings.index_path)
    assert recarregado.stats() == store.stats()
    assert recarregado.search("multa diária", top_k=1)[0].article == "Art. 5º"


def test_store_load_de_caminho_inexistente(tmp_path: Path):
    assert DocumentStore.load(tmp_path / "nao-existe.json").stats()["documents"] == 0


def test_chunks_of_ordenado(store: DocumentStore):
    documento = next(iter(store.documents.values()))
    ordinais = [c.ordinal for c in store.chunks_of(documento.id)]
    assert ordinais == sorted(ordinais)
