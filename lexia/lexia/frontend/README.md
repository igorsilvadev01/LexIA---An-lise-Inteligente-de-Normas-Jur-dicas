# LexIA — frontend

Interface React 19 + TypeScript (Vite) para o backend do LexIA: carga do corpus, busca híbrida,
extração estruturada e painel de métricas.

```bash
npm install
npm run dev        # http://localhost:5173 (espera a API em http://localhost:8000)
npm test           # Vitest + Testing Library
npm run typecheck
npm run lint
npm run build
```

A URL da API pode ser trocada com `VITE_API_URL`. Documentação geral no
[README raiz](../README.md) e em [`docs/`](../docs).
