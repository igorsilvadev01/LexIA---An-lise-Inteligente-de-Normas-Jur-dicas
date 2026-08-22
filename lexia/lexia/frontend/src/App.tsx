import { useCallback, useEffect, useState } from 'react'
import './App.css'
import { api } from './api'
import { DocumentsPanel } from './components/DocumentsPanel'
import { ExtractionPanel } from './components/ExtractionPanel'
import { MetricsPanel } from './components/MetricsPanel'
import { SearchPanel } from './components/SearchPanel'
import type { DocumentSummary, EvaluationResponse, ExtractionResult, Stats } from './types'

export default function App() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null)
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null)
  const [extracting, setExtracting] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    const [docs, currentStats] = await Promise.all([api.documents(), api.stats()])
    setDocuments(docs)
    setStats(currentStats)
    return docs
  }, [])

  const guard = useCallback(
    async <T,>(action: () => Promise<T>): Promise<T | undefined> => {
      setError(null)
      try {
        return await action()
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : 'Erro inesperado')
        return undefined
      }
    },
    [],
  )

  useEffect(() => {
    // o setState só ocorre depois do await, evitando renders em cascata
    void refresh().catch((cause: unknown) =>
      setError(cause instanceof Error ? cause.message : 'Erro inesperado'),
    )
  }, [refresh])

  const selected = documents.find((doc) => doc.id === selectedId) ?? null

  return (
    <div className="app">
      <header className="hero">
        <div>
          <h1>LexIA</h1>
          <p>
            Ingestão, indexação e extração estruturada de normas jurídicas — busca híbrida
            BM25 + vetorial, extração por regras ou LLM, e métricas contra golden set.
          </p>
        </div>
        {stats && (
          <ul className="hero-stats">
            <li>
              <strong>{stats.documents}</strong> documentos
            </li>
            <li>
              <strong>{stats.chunks}</strong> chunks
            </li>
            <li>
              <strong>{stats.vocab_size.toLocaleString('pt-BR')}</strong> termos no vocabulário
            </li>
          </ul>
        )}
      </header>

      {error && <p role="alert" className="error">{error}</p>}

      <main>
        <DocumentsPanel
          documents={documents}
          selectedId={selectedId}
          onSelect={(id) => {
            setSelectedId(id)
            setExtraction(null)
          }}
          onLoadCorpus={async () => {
            await guard(async () => {
              await api.loadCorpus()
              await refresh()
            })
          }}
          onUpload={async (file) => {
            await guard(async () => {
              const doc = await api.upload(file)
              await refresh()
              setSelectedId(doc.id)
            })
          }}
          onIngestText={async (text) => {
            await guard(async () => {
              const doc = await api.ingestText(text)
              await refresh()
              setSelectedId(doc.id)
            })
          }}
          onRemove={async (id) => {
            await guard(async () => {
              await api.remove(id)
              if (id === selectedId) {
                setSelectedId(null)
                setExtraction(null)
              }
              await refresh()
            })
          }}
        />

        <SearchPanel
          hasSelection={Boolean(selectedId)}
          onSearch={async (query, topK, restrict) => {
            const response = await guard(() =>
              api.search(query, topK, restrict ? (selectedId ?? undefined) : undefined),
            )
            return response?.hits ?? []
          }}
        />

        <ExtractionPanel
          documentLabel={selected?.source ?? null}
          result={extraction}
          loading={extracting}
          onExtract={async () => {
            if (!selectedId) return
            setExtracting(true)
            const result = await guard(() => api.extract(selectedId))
            if (result) setExtraction(result)
            setExtracting(false)
          }}
        />

        <MetricsPanel
          evaluation={evaluation}
          loading={evaluating}
          onEvaluate={async () => {
            setEvaluating(true)
            const result = await guard(() => api.evaluate())
            if (result) setEvaluation(result)
            setEvaluating(false)
          }}
        />
      </main>

      <footer>
        Backend FastAPI em <code>http://localhost:8000</code> · docs interativos em{' '}
        <code>/docs</code>
      </footer>
    </div>
  )
}
