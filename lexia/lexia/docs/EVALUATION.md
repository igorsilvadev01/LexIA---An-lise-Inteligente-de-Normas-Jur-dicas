# Relatório de avaliação — LexIA

- Backend de extração: **rules**
- Documentos avaliados: **5**
- Macro-F1: **0.972** · Micro-F1: **0.943**
- Gerado em: 2026-08-21 15:42:56 UTC

## Métricas por campo

| Campo | Precisão | Revocação | F1 | Itens no golden | Itens previstos |
| --- | --- | --- | --- | --- | --- |
| `norm_type` | 1.000 | 1.000 | 1.000 | 5 | 5 |
| `number` | 1.000 | 1.000 | 1.000 | 5 | 5 |
| `year` | 1.000 | 1.000 | 1.000 | 5 | 5 |
| `issuing_body` | 1.000 | 1.000 | 1.000 | 5 | 5 |
| `publication_date` | 1.000 | 1.000 | 1.000 | 5 | 5 |
| `effective_date` | 1.000 | 1.000 | 1.000 | 5 | 5 |
| `subject` | 1.000 | 1.000 | 1.000 | 5 | 5 |
| `obligations` | 0.867 | 0.684 | 0.765 | 19 | 15 |
| `deadlines` | 1.000 | 0.938 | 0.968 | 16 | 15 |
| `penalties` | 1.000 | 0.923 | 0.960 | 13 | 12 |
| `references` | 1.000 | 1.000 | 1.000 | 7 | 7 |

## Recuperação

| Métrica | Valor |
| --- | --- |
| queries | 12 |
| top_k | 5 |
| recall@1 | 0.8333 |
| recall@5 | 1 |
| mrr | 0.9028 |

## Por documento

| Documento | Macro-F1 | Campos mais fracos |
| --- | --- | --- |
| portaria-45-2024.txt | 0.727 | `obligations`, `deadlines`, `penalties` |
| lei-4444-2021.txt | 0.977 | `obligations` |
| resolucao-118-2022.txt | 0.977 | `obligations` |
| decreto-9876-2019.txt | 1.000 | — |
| instrucao-normativa-27-2023.txt | 1.000 | — |
