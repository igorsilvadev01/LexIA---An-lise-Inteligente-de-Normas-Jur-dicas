from app.extraction import rules


def test_cabecalho_tipo_numero_e_datas(lei_text: str):
    norm, _ = rules.extract(lei_text)
    assert norm.norm_type == "lei"
    assert norm.number == "4.444"
    assert norm.year == 2021
    assert norm.publication_date == "2021-03-12"
    assert norm.effective_date == "2021-07-01"


def test_orgao_e_ementa(lei_text: str):
    norm, _ = rules.extract(lei_text)
    assert norm.issuing_body == "PRESIDÊNCIA DA REPÚBLICA"
    assert norm.subject is not None and norm.subject.startswith("Dispõe sobre o tratamento")


def test_obrigacoes_com_ator_artigo_e_evidencia(lei_text: str):
    norm, _ = rules.extract(lei_text)
    artigos = {o.article for o in norm.obligations}
    assert {"Art. 3º", "Art. 4º", "Art. 5º", "Art. 6º"} <= artigos
    art4 = next(o for o in norm.obligations if o.article == "Art. 4º")
    assert art4.actor == "O controlador"
    assert "15 (quinze) dias" in art4.evidence
    assert all(o.evidence in lei_text for o in norm.obligations)


def test_cabecalho_de_capitulo_nao_e_obrigacao(lei_text: str):
    """'DOS DEVERES DOS ÓRGÃOS PÚBLICOS' contém 'deve' mas não é norma."""
    norm, _ = rules.extract(lei_text)
    assert not any("DEVERES" in o.action for o in norm.obligations)


def test_prazos_normalizados(lei_text: str):
    norm, _ = rules.extract(lei_text)
    assert ("Art. 4º", 15, "dias") in [(d.article, d.value, d.unit) for d in norm.deadlines]
    assert ("Art. 6º", 2, "dias") in [(d.article, d.value, d.unit) for d in norm.deadlines]


def test_penalidades_classificadas_com_valor(lei_text: str):
    norm, _ = rules.extract(lei_text)
    multa = next(p for p in norm.penalties if p.kind == "multa")
    assert multa.amount == "R$ 50.000.000,00"
    assert {"advertencia", "multa", "suspensao"} <= {p.kind for p in norm.penalties}


def test_referencias_canonizadas_sem_auto_referencia(lei_text: str):
    norm, _ = rules.extract(lei_text)
    assert norm.references == ["Lei nº 13.709/2018", "Decreto nº 9.876/2019"]
    assert "Lei nº 4.444/2021" not in norm.references


def test_data_numerica_e_vigencia_na_publicacao(portaria_text: str):
    norm, _ = rules.extract(portaria_text)
    assert norm.norm_type == "portaria"
    assert norm.publication_date == "2024-02-09"
    assert norm.effective_date == "2024-02-09"


def test_limitacao_conhecida_do_baseline(portaria_text: str):
    """Sem verbo modal ('Compete ao', 'É vedado') o baseline não vê obrigação.

    Este teste documenta a limitação medida em docs/EVALUATION.md e é a
    justificativa para o backend de LLM.
    """
    norm, _ = rules.extract(portaria_text)
    assert norm.obligations == []


def test_avisos_quando_cabecalho_desconhecido():
    norm, warnings = rules.extract("Documento sem cabeçalho normativo algum.")
    assert norm.norm_type == "desconhecido"
    assert any("cabeçalho" in w for w in warnings)
    assert any("vigência" in w for w in warnings)
