from app.dates import parse_pt_date
from app.text import normalize_key, normalize_whitespace, sentences, strip_accents, tokenize


def test_strip_accents_preserva_tamanho():
    assert strip_accents("Resolução") == "Resolucao"
    assert len(strip_accents("Ação órgão")) == len("Ação órgão")


def test_normalize_whitespace_junta_hifenizacao_de_pdf():
    assert normalize_whitespace("trans-\nparência") == "transparência"


def test_normalize_whitespace_colapsa_espacos_e_linhas():
    assert normalize_whitespace("  a   b \n\n\n\n c  ") == "a b\n\nc"


def test_tokenize_remove_stopwords_e_acentos():
    assert tokenize("O prazo de 15 dias para o órgão") == ["prazo", "15", "dias", "orgao"]


def test_tokenize_pode_manter_stopwords():
    assert "de" in tokenize("prazo de dias", remove_stopwords=False)


def test_normalize_key_ignora_pontuacao_e_caixa():
    assert normalize_key("Lei nº 13.709/2018") == normalize_key("lei n 13 709 2018")


def test_sentences_nao_quebra_em_abreviacao_de_artigo():
    text = "Art. 3º O órgão deverá publicar o relatório. Art. 4º O prazo é de 15 dias."
    result = sentences(text)
    assert len(result) == 2
    assert result[0].startswith("Art. 3º")
    assert result[1].startswith("Art. 4º")


def test_parse_pt_date_formato_longo_e_numerico():
    assert parse_pt_date("de 12 de março de 2021") == "2021-03-12"
    assert parse_pt_date("1º de julho de 2021") == "2021-07-01"
    assert parse_pt_date("PORTARIA Nº 45, DE 09/02/2024") == "2024-02-09"


def test_parse_pt_date_retorna_none_sem_data():
    assert parse_pt_date("entra em vigor na data de sua publicação") is None
    assert parse_pt_date("32 de dezembro de 2020") is None
