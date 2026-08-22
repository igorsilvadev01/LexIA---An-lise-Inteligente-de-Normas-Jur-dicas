"""Prompts versionados para extração estruturada.

Versionar prompt é o que torna a iteração mensurável: cada versão é avaliada
com o mesmo golden set (`make eval`), e o relatório registra qual prompt gerou
qual F1. O histórico abaixo documenta *por que* cada mudança foi feita.

Changelog
---------
**v1** — primeira versão: schema em texto + "responda em JSON".
Problemas observados no golden set:

* o modelo devolvia JSON dentro de ``` blocos, quebrando o parser;
* inventava ``issuing_body`` quando o cabeçalho não trazia o órgão;
* devolvia prazos como texto ("quinze dias") em vez de ``value``/``unit``;
* parafraseava a evidência, impossibilitando auditoria.

**v2** — mudanças e efeito pretendido:

1. "Responda **apenas** com JSON válido, sem markdown" — elimina o erro de parser.
2. Regra explícita de abstenção (`null` em vez de adivinhar) — reduz falso positivo
   em campos de cabeçalho, priorizando precisão.
3. ``value``/``unit`` numéricos obrigatórios em prazos, com exemplo — normaliza o campo.
4. ``evidence`` deve ser **cópia literal** do documento — habilita auditoria e
   permite validação automática (a evidência precisa existir no texto).
5. Ordem fixa dos campos e "cite o artigo" — reduz omissão de ``article``.
"""

from __future__ import annotations

SCHEMA_HINT = """{
  "norm_type": "lei|decreto|resolucao|portaria|instrucao_normativa|medida_provisoria|desconhecido",
  "number": "string ou null",
  "year": "inteiro ou null",
  "issuing_body": "string ou null",
  "publication_date": "YYYY-MM-DD ou null",
  "effective_date": "YYYY-MM-DD ou null",
  "subject": "ementa em uma frase ou null",
  "obligations": [{"actor": "string ou null", "action": "string", "article": "Art. Nº", "evidence": "trecho literal"}],
  "deadlines": [{"description": "string", "value": 15, "unit": "dias|meses|anos|horas|indefinido", "article": "Art. Nº", "evidence": "trecho literal"}],
  "penalties": [{"description": "string", "kind": "multa|advertencia|suspensao|cassacao|outra", "amount": "string ou null", "article": "Art. Nº", "evidence": "trecho literal"}],
  "references": ["Lei nº 13.709/2018"]
}"""

SYSTEM_V1 = "Você é um assistente que extrai informações de normas jurídicas brasileiras."

SYSTEM_V2 = (
    "Você é um analista jurídico-técnico especializado em normas brasileiras. "
    "Sua tarefa é extração factual, não interpretação. "
    "Responda APENAS com JSON válido (sem markdown, sem comentários, sem texto antes ou depois)."
)

USER_V1 = """Extraia as informações da norma abaixo e responda em JSON com o formato:
{schema}

Norma:
{document}
"""

USER_V2 = """Extraia os campos do schema a partir do documento normativo delimitado por <documento>.

Regras obrigatórias:
1. Responda apenas com um objeto JSON válido no formato exato abaixo. Sem markdown.
2. Se um campo não estiver explícito no documento, use null (ou lista vazia). NUNCA invente.
3. Datas sempre em ISO-8601 (YYYY-MM-DD).
4. Em "deadlines", "value" é inteiro e "unit" é uma das opções do schema.
   Ex.: "no prazo de 15 (quinze) dias" -> value=15, unit="dias".
5. "evidence" deve ser CÓPIA LITERAL de um trecho do documento (sem paráfrase).
6. Sempre informe "article" no formato "Art. 3º" quando o trecho estiver em um artigo.
7. Uma obrigação por dever distinto; não agrupe deveres de artigos diferentes.

Schema:
{schema}

<documento>
{document}
</documento>
"""

PROMPTS: dict[str, dict[str, str]] = {
    "v1": {"system": SYSTEM_V1, "user": USER_V1},
    "v2": {"system": SYSTEM_V2, "user": USER_V2},
}

DEFAULT_VERSION = "v2"


def build_prompt(document: str, version: str = DEFAULT_VERSION) -> tuple[str, str]:
    """Devolve ``(system, user)`` para a versão pedida."""
    if version not in PROMPTS:
        raise KeyError(f"prompt '{version}' inexistente; disponíveis: {sorted(PROMPTS)}")
    template = PROMPTS[version]
    return template["system"], template["user"].format(schema=SCHEMA_HINT, document=document)


REPAIR_INSTRUCTION = (
    "A resposta anterior não pôde ser validada. Erro do validador:\n{error}\n\n"
    "Responda novamente APENAS com o JSON corrigido, respeitando o schema."
)
