# Arquitetura e decisões técnicas

Este documento explica **por que** cada peça é como é. O código está em `backend/app/`.

## Visão geral

```
                    ┌──────────────────────── frontend/ (React + TS) ───────────────────────┐
                    │  DocumentsPanel   SearchPanel   ExtractionPanel   MetricsPanel        │
                    └───────────────────────────────┬──────────────────────────────────────┘
                                                    │ fetch (api.ts)
┌───────────────────────────────────────────────────▼──────────────────────────────────────┐
│ api.py (FastAPI)                                                                         │
│  /api/documents{,/text,/upload}  /api/search  /api/{id}/extract  /api/evaluate           │
└───┬─────────────────┬─────────────────────────┬───────────────────────┬─────────────────┘
    │                 │                         │                       │
 ingestion.py     store.py                extraction/            evaluation/
 (TXT/MD/PDF)   chunking + índices     rules.py | llm.py       metrics.py + runner.py
                       │                  service.py                    │
                index.py (BM25,        prompts.py (v1/v2)        golden.json + retrieval.json
                TF-IDF) + retrieval.py       │                          │
                       └──── SearchHit ──────┴──── LegalNorm ───────────┘
```

Fluxo de dados: bytes → texto normalizado → `Chunk[]` → índices → `SearchHit[]`;
texto → backend de extração → `LegalNorm` → métricas contra golden set.

## Decisões

### 1. Chunking por artigo, não por tamanho fixo

Cortar a cada N caracteres quebra o artigo no meio e produz respostas sem âncora legal. O
`chunking.py` detecta `Art. 1º` / `Artigo 2º`, propaga o capítulo/seção corrente como metadado e só
então aplica limite de tamanho (com sobreposição) para artigos longos. Cada chunk carrega
`start_char`/`end_char` e um ID determinístico (SHA-1 de `document_id` + offsets), então:

- a mesma ingestão sempre gera os mesmos IDs (testável, diffável, cacheável);
- toda extração pode ser rastreada de volta ao trecho exato — requisito prático em domínio jurídico.

### 2. Busca híbrida com Reciprocal Rank Fusion

Consulta jurídica é bimodal: metade é termo exato (“Lei nº 13.709/2018”, “Art. 7º”), metade é
semântica (“prazo para responder o titular”). BM25 acerta a primeira, similaridade de vetores a
segunda. Como score BM25 (não limitado) e cosseno (0–1) não são comparáveis, a fusão é por
**posição** e não por valor:

```
RRF(d) = Σ_r  peso_r / (k + posição_r(d))        k = 60
```

Isso dá robustez sem calibrar escalas. `store.search` ainda expõe `lexical_score` e
`semantic_score` separados, para o frontend mostrar de onde veio o resultado.

O filtro por documento é aplicado **dentro** dos índices (`allowed_ids`), não depois do corte de
top-k — caso contrário uma busca restrita a um documento poderia devolver lista vazia mesmo com
trechos relevantes (foi exatamente esse o bug pego pelo teste
`test_store_busca_pode_filtrar_por_documento`).

### 3. Vector store local em vez de serviço externo

`TfidfIndex` é TF-IDF (tf sublinear) + cosseno, com a mesma interface (`add`/`search`) de um
Chroma/FAISS. Motivo: o projeto precisa rodar em qualquer máquina, sem chave e sem container, e o
avaliador precisa ver o mecanismo, não uma chamada opaca. A troca por embeddings densos é local:
substituir a classe, mantendo `retrieval.py`, `store.py` e a API intactos.

### 4. Dois backends de extração sob o mesmo schema

`LegalNorm` (Pydantic) é o contrato único. `rules.py` implementa o baseline determinístico;
`llm.py` chama Anthropic/OpenAI. Consequências:

- os dois são avaliados pelas **mesmas** métricas → comparação justa entre regras, prompt v1 e v2;
- o `ExtractionService` degrada com elegância: se o LLM falhar (rede, JSON inválido nas duas
  tentativas, chave ausente), ele **cai para as regras** e registra o motivo em `warnings`, em vez
  de devolver 500;
- a resposta traz proveniência (`backend`, `model`, `prompt_version`, `latency_ms`) — sem isso não
  se sabe qual configuração produziu qual número.

### 5. Robustez do LLM: validar, reparar, então desistir

`llm.py` remove cercas de markdown, extrai o primeiro objeto JSON balanceado e valida com Pydantic.
Se falhar, reenvia **uma** vez incluindo a mensagem de erro do validador ("repair prompt"). Se
falhar de novo, lança `LLMError`, que o serviço converte em fallback. O transporte HTTP é injetável
(`Transport`), o que permite testar todo esse caminho — inclusive JSON truncado e schema inválido —
sem chamar API paga.

### 6. Avaliação: o projeto se mede sozinho

`evaluation/metrics.py` implementa:

- **campos escalares** (tipo, número, datas…) por igualdade normalizada (acentos/caixa/pontuação);
- **ementa** (`subject`) por similaridade de Jaccard sobre tokens, com limiar — comparar frase longa
  por igualdade exata seria inútil;
- **listas** (obrigações, prazos, penalidades) por pareamento guloso 1-para-1 acima de um limiar de
  similaridade, gerando TP/FP/FN honestos;
- **macro-F1** (média entre campos, dá peso igual a campo raro) e **micro-F1** (agregado, reflete
  volume);
- **recall@k** e **MRR** para a busca, contra `data/eval/retrieval.json`.

`python -m app.cli eval --min-macro-f1 0.95` sai com código 2 se a qualidade cair — a métrica serve
como *gate* de CI, não como número em slide.

### 7. Configuração por ambiente, sem segredo em disco

`config.py` lê tudo de variáveis de ambiente com defaults sãos (`LEXIA_EXTRACTOR`,
`LEXIA_LLM_PROVIDER`, `LEXIA_LLM_MODEL`, `LEXIA_PROMPT_VERSION`, `LEXIA_CHUNK_MAX_CHARS`,
`LEXIA_CHUNK_OVERLAP`, `LEXIA_TOP_K`, `LEXIA_PERSIST`). Chaves de API só vêm do ambiente; nenhuma é
escrita em arquivo ou comitada. `Settings` é injetável, e é por isso que os testes rodam contra
diretórios temporários sem tocar em `data/`.

### 8. Frontend enxuto e testável

React + TypeScript com Vite, sem biblioteca de estado: um `App` que mantém documentos, seleção,
extração e avaliação, e quatro painéis burros que recebem props. A camada de rede é um único módulo
(`src/api.ts`) com tipos espelhando os modelos Pydantic e um `ApiError` que preserva o status HTTP —
isso permite testar a UI com o `api` mockado (vitest + React Testing Library, consultas por papel
acessível) sem servidor no ar.

## Limites conscientes

| Escolha | Custo aceito | Caminho de evolução |
| --- | --- | --- |
| TF-IDF local | não captura sinonímia | trocar a classe por embeddings (Chroma/FAISS) |
| JSON como persistência | não escala, sem concorrência | Postgres + pgvector |
| Regras como baseline | perde formulações fora do padrão | backend LLM já implementado |
| Corpus fictício de 5 normas | golden set pequeno | ampliar anotação; métricas já existem |

## Uma lição do próprio desenvolvimento

O painel de métricas quebrou em produção com os testes verdes: a API devolve `field_scores` e o
componente lia `report.fields`, mas a fixture de teste também dizia `fields`. Mock inventado à mão
concorda com o bug em vez de detectá-lo. Como o contrato está publicado no OpenAPI, a fixture passou
a ser conferida contra a resposta real de `POST /api/evaluate`; o passo seguinte natural é gerar os
tipos do frontend a partir do `openapi.json` para que a divergência quebre no `tsc`, não na tela.
