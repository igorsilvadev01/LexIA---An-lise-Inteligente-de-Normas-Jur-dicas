import type {
  DocumentSummary,
  EvaluationResponse,
  ExtractionResult,
  SearchHit,
  Stats,
} from './types'
import { demoDocuments, demoEvaluation, demoExtraction, demoHits, demoStats } from './demo-data'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
export const IS_DEMO = import.meta.env.VITE_DEMO_MODE === 'true'
let documentsInDemo = [...demoDocuments]

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers:
      init?.body instanceof FormData
        ? init?.headers
        : { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new ApiError(detail || `HTTP ${response.status}`, response.status)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  stats: () => IS_DEMO ? Promise.resolve(demoStats(documentsInDemo)) : request<Stats>('/api/stats'),
  documents: () => IS_DEMO ? Promise.resolve([...documentsInDemo]) : request<DocumentSummary[]>('/api/documents'),
  loadCorpus: () => request<{ loaded: number; documents: DocumentSummary[] }>('/api/corpus/load', {
    method: 'POST',
  }),
  ingestText: (text: string, source = 'entrada-manual.txt') =>
    request<DocumentSummary>('/api/documents/text', {
      method: 'POST',
      body: JSON.stringify({ text, source }),
    }),
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<DocumentSummary>('/api/documents/upload', { method: 'POST', body: form })
  },
  remove: (documentId: string) =>
    request<void>(`/api/documents/${documentId}`, { method: 'DELETE' }),
  search: (query: string, topK: number, documentId?: string) =>
    request<{ query: string; hits: SearchHit[] }>('/api/search', {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK, document_id: documentId ?? null }),
    }),
  extract: (documentId: string) =>
    request<ExtractionResult>(`/api/documents/${documentId}/extract`, { method: 'POST' }),
  evaluate: () => request<EvaluationResponse>('/api/evaluate', { method: 'POST' }),
}

if (IS_DEMO) {
  api.loadCorpus = async () => {
    documentsInDemo = [...demoDocuments]
    return { loaded: documentsInDemo.length, documents: [...documentsInDemo] }
  }
  api.ingestText = async (text: string, source = 'entrada-manual.txt') => {
    const document = { id: `demo-${Date.now()}`, title: 'TEXTO ADICIONADO NA DEMONSTRAÇÃO', source, n_chunks: Math.max(1, Math.ceil(text.length / 500)), n_chars: text.length }
    documentsInDemo = [document, ...documentsInDemo]
    return document
  }
  api.upload = async (file: File) => api.ingestText(`Arquivo demonstrativo: ${file.name}`, file.name)
  api.remove = async (documentId: string) => { documentsInDemo = documentsInDemo.filter((item) => item.id !== documentId) }
  api.search = async (_query: string, topK: number, documentId?: string) => ({ query: _query, hits: demoHits.filter((hit) => !documentId || hit.document_id === documentId).slice(0, topK) })
  api.extract = async (documentId: string) => ({ ...demoExtraction, document_id: documentId })
  api.evaluate = async () => demoEvaluation
}
