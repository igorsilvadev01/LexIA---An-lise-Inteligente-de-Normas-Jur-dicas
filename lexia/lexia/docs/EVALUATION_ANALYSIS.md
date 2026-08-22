# Leitura crítica das métricas

`docs/EVALUATION.md` é **gerado** por `python -m app.cli eval --out ../docs/EVALUATION.md`
e sobrescrito a cada execução. Este arquivo guarda a interpretação (escrita à mão) dos números.

## Como cada métrica é calculada

- Campos escalares (`norm_type`, `number`, `year`, `issuing_body`, datas, `subject`):
  comparação normalizada (minúsculas, sem acento). Um acerto = 1 TP; divergência = 1 FP + 1 FN.
- Campos de lista (`obligations`, `deadlines`, `penalties`, `references`): casamento guloso
  por similaridade de conjunto de tokens (Jaccard) com limiar, para não punir diferenças de pontuação.
  Sobras da predição são FP, sobras do golden são FN.
- `macro_f1` = média simples dos F1 por campo (dá o mesmo peso a campo raro e campo comum).
  `micro_f1` = agregação global de TP/FP/FN (dominado pelos campos de lista, que têm mais itens).
- Recuperação: 12 consultas anotadas em `data/eval/retrieval.json` com o artigo esperado.
  `recall@k` = fração das consultas em que o artigo correto aparece no top-k;
  `mrr` = média de 1/posição do primeiro acerto.

## O que os números dizem

- Metadados (tipo, número, ano, órgão, datas, ementa): F1 = 1.000. Regex sobre o cabeçalho da
  norma resolve bem esse recorte — não há mérito de IA aqui, e o relatório não finge que há.
- `references` = 1.000: citações a outras normas seguem padrão rígido (`Lei nº 13.709/2018`).
- `deadlines` (0.968) e `penalties` (0.960): precisão 1.000 e revocação abaixo de 1 — o extrator
  **não inventa**, apenas deixa passar formulações fora dos padrões previstos.
- `obligations` = 0.765 é o gargalo real e está concentrado na Portaria 45/2024
  (macro-F1 0.727 nesse documento).
- Recuperação: `recall@5` = 1.000 com `mrr` = 0.903 significa que o trecho certo praticamente
  sempre entra no top-5 e quase sempre em 1º lugar; os erros são de ordenação, não de cobertura.

## Por que a Portaria pontua pior (e por que ela ficou assim)

A Portaria foi escrita de propósito com deveres redigidos **sem verbo modal explícito**:

- "Compete ao gestor local..."
- "Cabe ao órgão receptor..."
- "É vedado..."
- "...publicará..."

O baseline determinístico procura marcadores como `deve`, `deverá`, `fica obrigado`, `obriga-se`.
Nenhum casa com as formas acima, então essas obrigações não são capturadas (FN).

Seria trivial adicionar "compete", "cabe", "é vedado" e futuro do presente à regex e levar o
número para perto de 1.000 — e seria **overfitting no golden set**: o ganho apareceria na métrica
sem melhorar a generalização para redações que não estão no corpus. A limitação foi mantida
visível e medida, que é exatamente o cenário em que um extrator por LLM justifica seu custo.

## Comparando baselines (regras vs. LLM)

```bash
# baseline offline (default, sem chave de API)
python -m app.cli eval

# extrator LLM, prompt v1
LEXIA_EXTRACTOR=llm LEXIA_LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... \
  LEXIA_PROMPT_VERSION=v1 python -m app.cli eval --out ../docs/EVALUATION_llm_v1.md

# prompt v2 (mais instruções sobre obrigações implícitas)
LEXIA_EXTRACTOR=llm LEXIA_LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... \
  LEXIA_PROMPT_VERSION=v2 python -m app.cli eval --out ../docs/EVALUATION_llm_v2.md
```

Cada relatório registra `backend` e `prompt_version` no topo, então as versões são comparáveis
lado a lado. Nenhum resultado com LLM está publicado aqui: não foi executado neste repositório,
e reportar número não medido seria pior do que não ter número.

## Quality gate

`python -m app.cli eval --min-macro-f1 0.95` sai com código diferente de zero se a métrica cair
abaixo do limiar — é o mesmo comando que iria num passo de CI para impedir regressão de qualidade
na extração.
