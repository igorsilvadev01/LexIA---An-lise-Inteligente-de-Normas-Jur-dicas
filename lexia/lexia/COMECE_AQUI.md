# Comece aqui

Este é o guia rápido para (1) rodar o projeto na sua máquina, (2) publicar no GitHub e
(3) mandar o e-mail da vaga. O README é a documentação técnica; este arquivo é o passo a passo.

## 1. Rodar na sua máquina

Precisa de Python ≥ 3.10 e Node ≥ 20. Dois terminais:

```bash
# terminal 1 — backend
cd backend
python -m venv ../.venv
source ../.venv/bin/activate          # Windows: ..\.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.api:app --reload --port 8000
```

```bash
# terminal 2 — frontend
cd frontend
npm install
npm run dev                            # abre http://localhost:5173
```

Na interface: **Carregar corpus de exemplo** → digite uma busca (ou clique numa consulta sugerida)
→ clique num documento da lista → **Extrair campos** → **Rodar avaliação**.

Para conferir que tudo passa:

```bash
cd backend && pytest && ruff check .
cd ../frontend && npm test && npm run typecheck && npm run lint && npm run build
```

## 2. Publicar no GitHub

O `.gitignore` já exclui `node_modules/`, `.venv/`, `dist/`, caches e o índice gerado (`data/index/`).
Não há nenhuma chave de API no projeto — confirme com `git grep -i "api_key"` antes de publicar
(só devem aparecer nomes de variáveis de ambiente).

```bash
cd lexia
git init
git add .
git commit -m "LexIA: ingestão, busca híbrida e extração estruturada de normas jurídicas"
git branch -M main
# crie um repositório vazio em https://github.com/new (nome sugerido: lexia)
git remote add origin https://github.com/SEU_USUARIO/lexia.git
git push -u origin main
```

Depois de publicar, ajuste no GitHub:

- **About** (engrenagem à direita): descrição `Ingestão, indexação e extração estruturada de normas
  jurídicas — FastAPI + React, busca híbrida BM25+vetorial e métricas contra golden set` e topics
  `python`, `fastapi`, `react`, `typescript`, `nlp`, `information-retrieval`, `legal-tech`, `rag`.
- Confira se as imagens do README aparecem (elas vêm de `docs/screenshots/`).

Se quiser mostrar histórico em vez de um commit único, comite por etapa
(ingestão → índices → extração → avaliação → API → frontend → docs) — recrutador olha commits.

## 3. O e-mail

Para: `diretoria@jxreg.com.br` · Assunto: `Estágio Dev — JX`

Anexe o currículo, cole o link do repositório e os três parágrafos abaixo (a vaga pede "em 3 linhas
um problema técnico que você resolveu e como chegou à solução"). **Reescreva com suas palavras** —
tem que soar como você, e você precisa saber explicar cada frase numa entrevista.

> Construí o LexIA, que lê normas (TXT/MD/PDF), indexa por artigo e extrai campos jurídicos
> estruturados (obrigações, prazos, penalidades, referências) com métricas contra um golden set
> anotado: Macro-F1 0.972 na extração e Recall@5 1.000 / MRR 0.903 na busca.
>
> O problema técnico mais interessante foi a busca: consulta jurídica mistura termo exato
> ("Art. 7º", "Lei nº 13.709") com semântica ("prazo para responder o titular"), e nem BM25 nem
> similaridade vetorial resolvem sozinhos. Somar os scores não funciona porque as escalas são
> diferentes, então fundi os dois rankings com Reciprocal Rank Fusion — e para a busca restrita a um
> documento não voltar vazia, empurrei o filtro para dentro dos índices, antes do corte de top-k, em
> vez de filtrar o resultado depois.
>
> Mantive a extração por regras como baseline offline e um backend LLM opcional atrás do mesmo
> schema Pydantic (com reparo de JSON e fallback), justamente para poder medir o ganho de cada
> prompt no mesmo golden set. A limitação do baseline está documentada em vez de escondida:
> obrigações escritas como "Compete ao..." derrubam o F1 desse campo para 0.765, e "consertar" isso
> com mais regex seria overfitting na própria métrica.

Se perguntarem o que você faria a seguir: trocar o TF-IDF por embeddings de verdade (a interface já
é a mesma que Chroma/FAISS expõe), gerar os tipos do frontend a partir do `openapi.json`, e ampliar
o golden set — está tudo listado em `docs/ARCHITECTURE.md`.

## Perguntas que podem cair na entrevista (e onde está a resposta)

| Pergunta | Onde olhar |
| --- | --- |
| Por que chunking por artigo e não por tamanho fixo? | `backend/app/chunking.py`, `docs/ARCHITECTURE.md` |
| Como você combina busca lexical e vetorial? | `backend/app/retrieval.py` (RRF, k=60) |
| Como garante que o LLM devolve JSON válido? | `backend/app/extraction/llm.py` (validação, reparo, fallback) |
| Como sabe que o prompt v2 é melhor que o v1? | `backend/app/evaluation/`, `docs/EVALUATION_ANALYSIS.md` |
| O que é macro-F1 vs. micro-F1 aqui? | `docs/EVALUATION_ANALYSIS.md` |
| Que bug você encontrou testando? | `docs/TEST_EVIDENCE.md` (fim do arquivo) |
