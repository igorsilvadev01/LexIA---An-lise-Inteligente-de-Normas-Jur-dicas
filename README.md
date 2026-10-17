# LexIA — Análise Inteligente de Normas Jurídicas

Pipeline para ingestão, busca híbrida e extração estruturada de normas jurídicas, com avaliação automática contra um golden set anotado. O projeto oferece extrator determinístico por regras (offline) e um backend opcional por LLM, além de busca híbrida (BM25 + TF‑IDF) fusionada por RRF e métricas completas (Macro‑F1, Recall@k, MRR).

[![CI](https://github.com/igorsilvadev01/LexIA---An-lise-Inteligente-de-Normas-Jur-dicas/actions/workflows/ci.yml/badge.svg)](https://github.com/igorsilvadev01/LexIA---An-lise-Inteligente-de-Normas-Jur-dicas/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-brightgreen.svg)](lexia/lexia/LICENSE)

> Esta pasta principal reúne a documentação e os links para o projeto principal localizado em `lexia/lexia/`.

## Links rápidos
- Documentação técnica: `lexia/lexia/README.md`
- Guia rápido: `lexia/lexia/COMECE_AQUI.md`
- Backend (FastAPI): `lexia/lexia/backend`
- Frontend (React + TypeScript): `lexia/lexia/frontend`
- Dados de exemplo e golden set: `lexia/lexia/data`
- Documentação técnica detalhada: `lexia/lexia/docs`
- Licença: `lexia/lexia/LICENSE`

## Stack
- Linguagens: Python (backend) + TypeScript / React (frontend)
- Frameworks: FastAPI (backend), Vite + React 19 (frontend)
- Dependências notáveis: pydantic, uvicorn, pytest, vitest

## Quickstart mínimo
Pré-requisitos: Python ≥ 3.10 e Node ≥ 20.

Backend
```bash
cd lexia/lexia/backend
python -m venv ../../.venv
source ../../.venv/bin/activate   # Windows: ..\.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.api:app --reload --port 8000
```

Frontend
```bash
cd lexia/lexia/frontend
npm install
npm run dev    # http://localhost:5173
```

Testes (resumo)
```bash
cd lexia/lexia/backend && pytest
cd lexia/lexia/frontend && npm test
```

## Estrutura resumida
- `lexia/lexia/backend` — ingestão, chunking por artigo, indexação, extração (rules|llm), avaliação e API
- `lexia/lexia/frontend` — interface de carga, busca, extração e painel de métricas
- `lexia/lexia/data` — corpus de exemplo e golden set
- `lexia/lexia/docs` — arquitetura, API, avaliação, evidências e screenshots

## Contribuição
Leia `CONTRIBUTING.md` antes de abrir um PR. Os fluxos de lint e teste estão configurados para backend e frontend.

## Licença
MIT — veja `lexia/lexia/LICENSE`.
