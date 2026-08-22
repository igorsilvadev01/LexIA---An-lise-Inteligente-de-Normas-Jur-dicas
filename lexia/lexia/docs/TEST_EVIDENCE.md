# Evidência de que o código funciona

Todos os resultados abaixo foram produzidos nesta máquina, com os comandos exatamente como estão
escritos. As saídas completas estão em `docs/evidence/` — nenhum número aqui foi digitado à mão.

| Verificação | Comando | Resultado | Saída completa |
| --- | --- | --- | --- |
| Testes backend | `python -m pytest` | **113 passed**, cobertura **95.66%** (gate de 90%) | `docs/evidence/backend-pytest.txt` |
| Lint/format backend | `ruff check .` · `ruff format --check .` | `All checks passed!` · `30 files already formatted` | `docs/evidence/backend-ruff.txt` |
| Testes frontend | `npx vitest run` | **14 passed** (2 arquivos) | `docs/evidence/frontend-vitest.txt` |
| Tipos + lint + build frontend | `npm run typecheck` · `npx eslint .` · `npm run build` | sem erros · `✓ built` | `docs/evidence/frontend-checks.txt` |
| Avaliação end-to-end | `python -m app.cli eval` | Macro-F1 **0.972** · Micro-F1 **0.943** · Recall@5 **1.000** · MRR **0.903** | `docs/EVALUATION.md` |

## O que os testes de backend cobrem (113 testes)

- `test_text.py` — normalização, remoção de acentos, tokenização, segmentação de sentenças
  com proteção de abreviações (`art.`, `nº`, `inc.`), parsing de datas em português.
- `test_chunking.py` — um chunk por artigo, propagação de capítulo/seção, offsets que apontam
  para o texto original, IDs determinísticos, artigo longo dividido com sobreposição, parâmetros inválidos.
- `test_index.py` — BM25 (saturação de TF, penalização por tamanho), TF-IDF, cosseno,
  Reciprocal Rank Fusion, filtro por `allowed_ids`.
- `test_ingestion_store.py` — TXT/Markdown/PDF, extensão inválida, documento vazio, persistência
  em disco, ingestão idempotente, busca restrita a um documento, remoção com reindexação.
- `test_extraction_rules.py` — metadados, obrigações, prazos, penalidades, referências,
  cabeçalhos em caixa alta que **não** devem virar obrigação.
- `test_extraction_llm.py` — prompt montado, transporte injetado (sem rede), remoção de cercas
  markdown, reparo de JSON inválido, validação do schema, erro após segunda tentativa, fallback para regras.
- `test_evaluation.py` — precision/recall/F1, casamento guloso de listas, macro vs. micro,
  `recall@k`, MRR, renderização do markdown.
- `test_api.py` — os 12 endpoints, validação de payload (422), tipo não suportado (415),
  documento inexistente (404), cache de extração e `?refresh=true`, contrato do OpenAPI.
- `test_cli.py` — `ingest`, `search`, `extract`, `eval` e o quality gate `--min-macro-f1`.

O gate de qualidade é real: `python -m app.cli eval --min-macro-f1 0.99` sai com código **2**
(macro-F1 0.972 < 0.99), enquanto `--min-macro-f1 0.95` sai com **0**.

## O que os testes de frontend cobrem (14 testes)

`src/api.test.ts` — a camada HTTP: content-type correto no JSON, `document_id` propagado na busca
restrita, upload multipart sem content-type forçado, `204` sem corpo no DELETE, `ApiError` com status.

`src/App.test.tsx` — a aplicação com `fetch` mockado: carregamento inicial de estatísticas e
documentos, busca exibindo artigo e scores BM25/cosseno/RRF, consulta sugerida, busca restrita ao
documento selecionado, extração de campos, painel de métricas com destaque do campo fraco,
ingestão de texto colado, carregar corpus, remoção de documento e mensagem de erro quando a API falha.

## Verificação manual no navegador

O golden path foi executado com backend e frontend rodando de verdade
(`uvicorn app.api:app` + `npm run dev`); os prints estão em `docs/screenshots/`:

1. `01-visao-geral.png` — corpus carregado: 5 documentos, 45 chunks, 423 termos no vocabulário.
2. `02-busca-hibrida.png` — "prazo para responder pedido de acesso do titular" traz o Art. 4º em 1º
   lugar com BM25 16.588 / cos 0.588.
3. `03-extracao-estruturada.png` — Lei 4.444/2021 extraída em 2 ms: metadados, 4 obrigações,
   3 prazos, 3 penalidades, 2 normas citadas.
4. `04-metricas.png` — avaliação rodada pela UI, com `obligations` destacado por estar abaixo de 0.9.
5. `05-swagger.png` — OpenAPI gerado pelo FastAPI em `/docs`.

### Bug encontrado e corrigido nessa verificação

Rodar a avaliação pela UI deixava a tela branca: o backend serializa a lista de métricas como
`field_scores` e o componente lia `report.fields`, então `report.fields.map(...)` estourava. Os
testes de frontend não pegaram porque a fixture reproduzia o nome errado do campo — o mock estava
consistente com o bug, não com a API. A correção alinhou `types.ts`, `MetricsPanel.tsx` e a fixture
ao contrato real da API (conferido contra `POST /api/evaluate`). Lição registrada em
`docs/ARCHITECTURE.md`: fixture de teste que não vem do contrato real vira cúmplice do bug.
