import pytest

from app.chunking import article_segments, chunk_text


def test_um_chunk_por_artigo(lei_text: str):
    chunks = chunk_text(lei_text, "doc")
    articles = [c.article for c in chunks if c.article]
    assert articles == [f"Art. {n}º" for n in range(1, 10)]


def test_preambulo_vira_chunk_sem_artigo(lei_text: str):
    chunks = chunk_text(lei_text, "doc")
    assert chunks[0].article is None
    assert "LEI Nº 4.444" in chunks[0].text


def test_secao_e_propagada_para_o_chunk(lei_text: str):
    chunks = chunk_text(lei_text, "doc")
    art3 = next(c for c in chunks if c.article == "Art. 3º")
    assert art3.section is not None and "CAPÍTULO II" in art3.section


def test_offsets_apontam_para_o_texto_original(lei_text: str):
    for chunk in chunk_text(lei_text, "doc"):
        assert chunk.text in lei_text[chunk.start_char : chunk.end_char]


def test_ids_sao_deterministicos(lei_text: str):
    assert [c.id for c in chunk_text(lei_text, "doc")] == [c.id for c in chunk_text(lei_text, "doc")]


def test_artigo_longo_e_dividido_com_sobreposicao():
    corpo = "\n".join(f"Parágrafo {i} com texto suficiente para ocupar espaço." for i in range(40))
    texto = f"Art. 1º Início do artigo.\n{corpo}"
    chunks = chunk_text(texto, "doc", max_chars=300, overlap=60)
    assert len(chunks) > 1
    assert all(len(c.text) <= 300 for c in chunks)
    assert all(c.article == "Art. 1º" for c in chunks)


def test_paragrafo_gigante_e_fatiado_em_janelas():
    texto = "Art. 1º " + ("palavra " * 400)
    chunks = chunk_text(texto, "doc", max_chars=200, overlap=50)
    assert len(chunks) > 1
    assert all(len(c.text) <= 200 for c in chunks)


def test_documento_sem_artigos_gera_chunk_unico():
    chunks = chunk_text("Texto livre sem estrutura normativa.", "doc")
    assert len(chunks) == 1 and chunks[0].article is None


@pytest.mark.parametrize("max_chars,overlap", [(0, 0), (100, 100), (100, -1)])
def test_parametros_invalidos(max_chars: int, overlap: int):
    with pytest.raises(ValueError):
        chunk_text("Art. 1º texto", "doc", max_chars=max_chars, overlap=overlap)


def test_article_segments_cobre_todo_o_texto(lei_text: str):
    segments = article_segments(lei_text)
    assert segments[0][0] == 0
    assert segments[-1][1] == len(lei_text)
