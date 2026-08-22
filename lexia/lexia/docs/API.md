# API HTTP

Servidor: `uvicorn app.api:app --reload --port 8000` (dentro de `backend/`).
Documentação interativa (OpenAPI/Swagger): <http://localhost:8000/docs>.

| Método | Rota | O que faz |
| --- | --- | --- |
| GET | `/api/health` | status, versão e backend de extração ativo |
| GET | `/api/stats` | documentos, chunks, tamanho do vocabulário, caracteres |
| GET | `/api/documents` | lista documentos indexados |
| POST | `/api/documents/text` | ingere texto colado (`text`, `source`, `title`) |
| POST | `/api/documents/upload` | ingere arquivo `.txt`/`.md`/`.pdf` (multipart, máx. 10 MB) |
| POST | `/api/corpus/load` | ingere `data/corpus/` inteiro (idempotente) |
| GET | `/api/documents/{id}` | documento completo |
| GET | `/api/documents/{id}/chunks` | chunks com artigo, seção e offsets |
| DELETE | `/api/documents/{id}` | remove o documento e reindexa |
| POST | `/api/search` | busca híbrida (`query`, `top_k`, `document_id` opcional) |
| POST | `/api/documents/{id}/extract` | extração estruturada (`?refresh=true` ignora cache) |
| POST | `/api/evaluate` | roda a avaliação e devolve relatório + markdown |

Códigos de erro: `404` documento/golden inexistente · `413` upload acima de 10 MB ·
`415` extensão não suportada · `422` payload inválido (texto curto, `top_k` fora do intervalo).

## Exemplos

```bash
# carregar o corpus de exemplo
curl -X POST localhost:8000/api/corpus/load

# busca híbrida
curl -X POST localhost:8000/api/search -H 'Content-Type: application/json' \
  -d '{"query":"multa sobre o faturamento anual da plataforma","top_k":3}'
```

```json
{
  "query": "multa sobre o faturamento anual da plataforma",
  "hits": [
    {
      "chunk_id": "8f2c1d...-6",
      "document_id": "resolucao-118-2022...",
      "document_title": "AGÊNCIA NACIONAL DE REGULAÇÃO DIGITAL",
      "article": "Art. 7º",
      "text": "Art. 7º O descumprimento desta Resolução sujeita a plataforma digital à advertência e à multa de até 2% (dois por cento) do faturamento anual no País, limitada a R$ 30.000.000,00 por infração.",
      "score": 0.0328,
      "lexical_score": 9.412,
      "semantic_score": 0.284
    }
  ]
}
```

```bash
# extração estruturada
curl -X POST localhost:8000/api/documents/<id>/extract
```

```json
{
  "document_id": "lei-4444-2021...",
  "backend": "rules",
  "prompt_version": null,
  "model": null,
  "latency_ms": 3.4,
  "warnings": [],
  "norm": {
    "norm_type": "lei",
    "number": "4.444",
    "year": 2021,
    "issuing_body": "PRESIDÊNCIA DA REPÚBLICA",
    "publication_date": "2021-03-12",
    "effective_date": "2021-06-10",
    "subject": "Dispõe sobre a transparência de dados públicos...",
    "obligations": [
      {
        "subject": "o órgão público",
        "action": "deverá publicar em formato aberto...",
        "article": "Art. 3º",
        "evidence": "Art. 3º Os órgãos públicos deverão publicar..."
      }
    ],
    "deadlines": [
      { "description": "responder ao pedido de acesso", "value": 15, "unit": "dias", "article": "Art. 4º" }
    ],
    "penalties": [{ "kind": "multa", "amount": "R$ 50.000.000,00", "article": "Art. 8º" }],
    "references": ["Lei nº 13.709/2018", "Decreto nº 9.876/2019"]
  }
}
```

Com `LEXIA_EXTRACTOR=llm`, os campos `backend`, `model` e `prompt_version` mudam e `warnings`
registra qualquer reparo de JSON ou fallback para regras — a resposta sempre diz como foi produzida.

```bash
# avaliação (mesmo relatório do CLI, em JSON + markdown)
curl -X POST localhost:8000/api/evaluate | jq '.report.macro_f1, .report.retrieval'
```
