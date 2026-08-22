import { useState } from 'react'
import type { SearchHit } from '../types'

interface Props {
  onSearch: (query: string, topK: number, restrictToSelected: boolean) => Promise<SearchHit[]>
  hasSelection: boolean
}

const SUGESTOES = [
  'prazo para responder pedido de acesso do titular',
  'multa sobre o faturamento anual da plataforma',
  'relatório de impacto algorítmico',
]

export function SearchPanel({ onSearch, hasSelection }: Props) {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [restrict, setRestrict] = useState(false)
  const [hits, setHits] = useState<SearchHit[] | null>(null)
  const [loading, setLoading] = useState(false)

  const run = async (value: string) => {
    if (value.trim().length < 2) return
    setLoading(true)
    try {
      setHits(await onSearch(value, topK, restrict && hasSelection))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="panel">
      <h2>2. Busca híbrida (BM25 + vetorial)</h2>
      <form
        className="row"
        onSubmit={(event) => {
          event.preventDefault()
          void run(query)
        }}
      >
        <input
          type="search"
          aria-label="Consulta"
          placeholder="Pergunte em linguagem natural..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <label className="inline">
          top-k
          <input
            type="number"
            min={1}
            max={20}
            aria-label="top-k"
            value={topK}
            onChange={(event) => setTopK(Number(event.target.value))}
          />
        </label>
        <label className="inline">
          <input
            type="checkbox"
            checked={restrict}
            disabled={!hasSelection}
            onChange={(event) => setRestrict(event.target.checked)}
          />
          só no documento selecionado
        </label>
        <button type="submit" disabled={query.trim().length < 2 || loading}>
          {loading ? 'Buscando...' : 'Buscar'}
        </button>
      </form>

      <div className="chips">
        {SUGESTOES.map((sugestao) => (
          <button
            key={sugestao}
            type="button"
            className="chip"
            onClick={() => {
              setQuery(sugestao)
              void run(sugestao)
            }}
          >
            {sugestao}
          </button>
        ))}
      </div>

      {hits && hits.length === 0 && <p className="empty">Nenhum trecho encontrado.</p>}
      <ol className="hits">
        {hits?.map((hit) => (
          <li key={hit.chunk_id}>
            <header>
              <span className="tag">{hit.article ?? 'preâmbulo'}</span>
              <span className="doc-title">{hit.document_title}</span>
              <span className="scores">
                RRF {hit.score.toFixed(4)} · BM25 {hit.lexical_score.toFixed(3)} · cos{' '}
                {hit.semantic_score.toFixed(3)}
              </span>
            </header>
            <p>{hit.text}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
