# LexIA — Análise Inteligente de Normas Jurídicas

Pipeline para ingestão, busca híbrida e extração estruturada de normas jurídicas, com avaliação automática contra um golden set anotado. O projeto oferece extrator determinístico por regras (offline) e um backend opcional por LLM, além de busca híbrida (BM25 + TF‑IDF) fusionada por RRF e métricas completas (Macro‑F1, Recall@k, MRR).

> Esta pasta principal concentra o código e a documentação em `lexia/lexia/` — leia `COMECE_AQUI.md` para um passo a passo rápido.

Badges: (adicione badges de CI / cobertura quando o workflow estiver ativo)

## Links rápidos
- Documentação técnica: `lexia/lexia/README.md`
- Guia rápido: `lexia/lexia/COMECE_AQUI.md`
- Backend (FastAPI): `lexia/lexia/backend`
- Frontend (React + TypeScript): `lexia/lexia/frontend`
- Dados de exemplo e golden set: `lexia/lexia/data`
- Docs detalhados: `lexia/lexia/docs`
- Licença: `lexia/lexia/LICENSE` (MIT)

## Stack
- Linguagens: Python (backend) + TypeScript / React (frontend)
- Frameworks: FastAPI (backend), Vite + React 19 (frontend)
- Dependências notáveis: pydantic, uvicorn, pytest, vitest

## Quickstart mínimo
Pré-requisitos: Python ≥ 3.10 e Node ≥ 20

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
- `lexia/lexia/docs` — arquitetura, API, avaliação e evidências

## Contribuição
Por favor, leia `CONTRIBUTING.md` (criado na raiz). Siga os testes e lint configurados no repositório (ruff / eslint / vitest).

---

Se quiser que eu adicione badges de CI/cobertura, me informe o nome do workflow e eu atualizo este README com os links gerados pelo GitHub Actions.
