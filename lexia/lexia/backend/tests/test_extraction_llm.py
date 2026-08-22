import json

import pytest

from app.config import Settings
from app.extraction.llm import LLMError, LLMExtractor, http_transport, parse_json_payload
from app.extraction.prompts import PROMPTS, build_prompt
from app.extraction.service import ExtractionService

NORMA_VALIDA = {
    "norm_type": "lei",
    "number": "4.444",
    "year": 2021,
    "issuing_body": "PRESIDÊNCIA DA REPÚBLICA",
    "publication_date": "2021-03-12",
    "effective_date": "2021-07-01",
    "subject": "Dispõe sobre dados pessoais em serviços públicos digitais.",
    "obligations": [
        {
            "actor": "O controlador",
            "action": "responder pedidos de acesso em 15 dias",
            "article": "Art. 4º",
            "evidence": "no prazo de 15 (quinze) dias",
        }
    ],
    "deadlines": [{"description": "resposta ao titular", "value": 15, "unit": "dias", "article": "Art. 4º"}],
    "penalties": [{"description": "multa simples", "kind": "multa", "article": "Art. 7º"}],
    "references": ["Lei nº 13.709/2018"],
}


def test_build_prompt_v2_tem_regras_antialucinacao():
    system, user = build_prompt("texto", "v2")
    assert "APENAS com JSON" in system
    assert "NUNCA invente" in user
    assert "<documento>\ntexto\n</documento>" in user


def test_build_prompt_versao_inexistente():
    with pytest.raises(KeyError):
        build_prompt("texto", "v99")


def test_todas_as_versoes_tem_placeholders():
    for versao in PROMPTS:
        system, user = build_prompt("doc", versao)
        assert system and "doc" in user


def test_parse_json_tolera_cerca_markdown_e_texto_ao_redor():
    bruto = 'Claro! Aqui vai:\n```json\n{"norm_type": "lei"}\n```\nEspero ter ajudado.'
    assert parse_json_payload(bruto) == {"norm_type": "lei"}


def test_parse_json_sem_objeto():
    with pytest.raises(LLMError):
        parse_json_payload("desculpe, não consigo ajudar")


def test_extrator_llm_caminho_felz():
    chamadas = []

    def transport(system: str, user: str) -> str:
        chamadas.append((system, user))
        return json.dumps(NORMA_VALIDA)

    norm, warnings = LLMExtractor(transport).extract("Art. 4º ...")
    assert norm.number == "4.444"
    assert norm.deadlines[0].value == 15
    assert warnings == []
    assert len(chamadas) == 1


def test_extrator_llm_repara_resposta_invalida():
    respostas = ["não é json", json.dumps(NORMA_VALIDA)]

    def transport(system: str, user: str) -> str:
        return respostas.pop(0)

    norm, warnings = LLMExtractor(transport).extract("texto")
    assert norm.number == "4.444"
    assert any("reparo" in w for w in warnings)


def test_extrator_llm_falha_apos_reparo():
    def transport(system: str, user: str) -> str:
        return "{ ainda invalido }"

    with pytest.raises(LLMError):
        LLMExtractor(transport).extract("texto")


def test_extrator_llm_valida_schema_e_repara_campo_invalido():
    invalida = {**NORMA_VALIDA, "year": "vinte e um"}
    respostas = [json.dumps(invalida), json.dumps(NORMA_VALIDA)]

    def transport(system: str, user: str) -> str:
        return respostas.pop(0)

    norm, warnings = LLMExtractor(transport).extract("texto")
    assert norm.year == 2021 and warnings


def test_extrator_llm_trunca_documento_muito_grande():
    recebidos: list[str] = []

    def transport(system: str, user: str) -> str:
        recebidos.append(user)
        return json.dumps(NORMA_VALIDA)

    _, warnings = LLMExtractor(transport, max_document_chars=50).extract("x" * 5000)
    assert any("truncado" in w for w in warnings)
    assert len(recebidos[0]) < 5000


def test_http_transport_provedor_desconhecido():
    with pytest.raises(LLMError):
        http_transport(provider="inexistente")("s", "u")


def test_http_transport_sem_chave(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMError):
        http_transport(provider="anthropic")("s", "u")


def test_service_usa_regras_por_padrao(settings: Settings, lei_text: str):
    servico = ExtractionService(settings)
    assert servico.backend == "rules"
    resultado = servico.extract(document_id="doc", text=lei_text)
    assert resultado.backend == "rules"
    assert resultado.norm.number == "4.444"
    assert resultado.latency_ms >= 0


def test_service_usa_llm_quando_configurado(settings: Settings, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LEXIA_EXTRACTOR", "llm")
    servico = ExtractionService(Settings(), transport=lambda s, u: json.dumps(NORMA_VALIDA))
    resultado = servico.extract(document_id="doc", text="Art. 4º ...")
    assert resultado.backend == "llm"
    assert resultado.prompt_version == "v2"
    assert resultado.norm.number == "4.444"


def test_service_faz_fallback_para_regras_quando_llm_falha(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, lei_text: str
):
    monkeypatch.setenv("LEXIA_EXTRACTOR", "llm")

    def transport(system: str, user: str) -> str:
        return "resposta impossível de validar"

    resultado = ExtractionService(Settings(), transport=transport).extract(document_id="doc", text=lei_text)
    assert resultado.backend == "rules"
    assert any("LLM falhou" in w for w in resultado.warnings)
    assert resultado.norm.number == "4.444"
