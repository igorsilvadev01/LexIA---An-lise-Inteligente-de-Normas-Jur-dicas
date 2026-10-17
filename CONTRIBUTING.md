# Contributing para LexIA

Obrigado por considerar contribuir! Estas instruções ajudam a manter a qualidade do projeto e a facilitar revisões.

## Sumário rápido
- Abra issues para bugs e sugestões.
- Faça um fork, crie uma branch com nome descritivo e abra um Pull Request para `main`.
- Execute testes e lint antes do PR.

## Ambiente de desenvolvimento

Backend:
- Requisitos: Python ≥ 3.10

```bash
cd lexia/lexia/backend
python -m venv ../../.venv
source ../../.venv/bin/activate   # Windows: ..\.venv\Scripts\activate
pip install -e "[dev]"
```

Frontend:
- Requisitos: Node ≥ 20

```bash
cd lexia/lexia/frontend
npm install
npm run dev
```

## Testes e qualidade

Rodar testes backend:
```bash
cd lexia/lexia/backend
pytest
ruff check . && ruff format --check .
```

Rodar testes frontend:
```bash
cd lexia/lexia/frontend
npm test
npm run lint
npm run typecheck
```

## Fluxo de branches e PR
- Branches: `feature/<descrição>`, `fix/<descrição>`, `chore/<descrição>`.
- Commit messages: use mensagens claras (ex.: `feat: adicionar endpoint de busca por artigo`).
- Abra PRs com descrição do que muda, como testar localmente e qual o impacto nos testes/avaliação.

## Estilo de código
- Backend: Python (ruff configura as regras; line-length 110).
- Frontend: ESLint + Prettier configurados no projeto.

## Checklist para PR
- [ ] Testes locais passam (backend e frontend relevantes).
- [ ] Lint e formatação aplicados.
- [ ] Documentação atualizada se necessário (README, docs/).
- [ ] Caso altere o schema ou API, inclua impacto na avaliação (docs/EVALUATION_ANALYSIS.md).

## Contato
Mantenha comunicações na issue/PR. Para dúvidas rápidas, mencione um mantenedor no PR.
