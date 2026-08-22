import type {
  DocumentSummary,
  EvaluationResponse,
  ExtractionResult,
  SearchHit,
  Stats,
} from './types'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

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
  stats: () => request<Stats>('/api/stats'),
  documents: () => request<DocumentSummary[]>('/api/documents'),
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
