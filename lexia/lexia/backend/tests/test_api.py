import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.config import Settings
from app.store import DocumentStore


@pytest.fixture
def client(settings: Settings, store: DocumentStore) -> TestClient:
    return TestClient(create_app(settings, store=store))


@pytest.fixture
def client_vazio(settings: Settings) -> TestClient:
    return TestClient(create_app(settings, store=DocumentStore()))


def test_health(client: TestClient):
    corpo = client.get("/api/health").json()
    assert corpo["status"] == "ok"
    assert corpo["extractor_backend"] == "rules"


def test_stats(client: TestClient):
    corpo = client.get("/api/stats").json()
    assert corpo["documents"] == 5
    assert corpo["chunks"] > 20


def test_listar_documentos(client: TestClient):
    documentos = client.get("/api/documents").json()
    assert len(documentos) == 5
    assert all(doc["n_chunks"] > 0 for doc in documentos)


def test_ingestao_por_texto(client_vazio: TestClient):
    resposta = client_vazio.post(
        "/api/documents/text",
        json={
            "text": "PORTARIA Nº 9, DE 1º DE MARÇO DE 2020\n\nArt. 1º O órgão deverá publicar dados.",
            "source": "manual.txt",
        },
    )
    assert resposta.status_code == 201
    assert resposta.json()["n_chunks"] >= 1


def test_ingestao_por_texto_valida_tamanho_minimo(client_vazio: TestClient):
    assert client_vazio.post("/api/documents/text", json={"text": "curto"}).status_code == 422


def test_upload_de_arquivo(client_vazio: TestClient, minimal_pdf: bytes):
    resposta = client_vazio.post(
        "/api/documents/upload",
        files={"file": ("norma.pdf", minimal_pdf, "application/pdf")},
    )
    assert resposta.status_code == 201
    assert resposta.json()["source"] == "norma.pdf"


def test_upload_tipo_nao_suportado(client_vazio: TestClient):
    resposta = client_vazio.post(
        "/api/documents/upload", files={"file": ("x.docx", b"conteudo", "application/msword")}
    )
    assert resposta.status_code == 415


def test_carregar_corpus(client_vazio: TestClient):
    corpo = client_vazio.post("/api/corpus/load").json()
    assert corpo["loaded"] == 5
    assert client_vazio.post("/api/corpus/load").json()["loaded"] == 0  # idempotente


def test_busca_retorna_artigo_relevante(client: TestClient):
    corpo = client.post(
        "/api/search",
        json={"query": "multa sobre o faturamento anual da plataforma", "top_k": 3},
    ).json()
    assert corpo["hits"][0]["article"] == "Art. 7º"
    assert "faturamento anual" in corpo["hits"][0]["text"]
    assert len(corpo["hits"]) <= 3


def test_busca_valida_top_k(client: TestClient):
    assert client.post("/api/search", json={"query": "multa", "top_k": 999}).status_code == 422


def test_documento_e_chunks(client: TestClient):
    doc_id = client.get("/api/documents").json()[0]["id"]
    assert client.get(f"/api/documents/{doc_id}").json()["id"] == doc_id
    chunks = client.get(f"/api/documents/{doc_id}/chunks").json()
    assert chunks and chunks[0]["ordinal"] == 0


def test_documento_inexistente(client: TestClient):
    assert client.get("/api/documents/nao-existe").status_code == 404
    assert client.get("/api/documents/nao-existe/chunks").status_code == 404
    assert client.post("/api/documents/nao-existe/extract").status_code == 404
    assert client.delete("/api/documents/nao-existe").status_code == 404


def test_extracao_estruturada(client: TestClient):
    doc_id = next(doc["id"] for doc in client.get("/api/documents").json() if "lei-4444" in doc["source"])
    corpo = client.post(f"/api/documents/{doc_id}/extract").json()
    assert corpo["backend"] == "rules"
    assert corpo["norm"]["number"] == "4.444"
    assert corpo["norm"]["obligations"][0]["article"] == "Art. 3º"
    assert corpo["norm"]["references"] == ["Lei nº 13.709/2018", "Decreto nº 9.876/2019"]


def test_extracao_usa_cache_e_refresh(client: TestClient):
    doc_id = client.get("/api/documents").json()[0]["id"]
    primeiro = client.post(f"/api/documents/{doc_id}/extract").json()
    assert client.post(f"/api/documents/{doc_id}/extract").json() == primeiro
    atualizado = client.post(f"/api/documents/{doc_id}/extract?refresh=true").json()
    assert atualizado["norm"] == primeiro["norm"]


def test_remocao_de_documento(client: TestClient):
    doc_id = client.get("/api/documents").json()[0]["id"]
    assert client.delete(f"/api/documents/{doc_id}").status_code == 204
    assert client.get(f"/api/documents/{doc_id}").status_code == 404


def test_avaliacao_via_api(client: TestClient):
    corpo = client.post("/api/evaluate").json()
    assert corpo["report"]["n_documents"] == 5
    assert corpo["report"]["macro_f1"] > 0.9
    assert corpo["report"]["retrieval"]["mrr"] > 0.8
    assert "Relatório de avaliação" in corpo["markdown"]


def test_openapi_documentado(client: TestClient):
    esquema = client.get("/openapi.json").json()
    assert "/api/search" in esquema["paths"]
    assert esquema["info"]["title"] == "LexIA API"
