export interface DocumentSummary {
  id: string
  title: string
  source: string
  n_chunks: number
  n_chars: number
}

export interface SearchHit {
  chunk_id: string
  document_id: string
  document_title: string
  text: string
  score: number
  lexical_score: number
  semantic_score: number
  article: string | null
}

export interface Obligation {
  subject: string
  action: string
  article: string | null
  evidence: string | null
}

export interface Deadline {
  description: string
  value: number | null
  unit: string | null
  article: string | null
}

export interface Penalty {
  kind: string
  amount: string | null
  article: string | null
}

export interface LegalNorm {
  norm_type: string
  number: string | null
  year: number | null
  issuing_body: string | null
  publication_date: string | null
  effective_date: string | null
  subject: string | null
  obligations: Obligation[]
  deadlines: Deadline[]
  penalties: Penalty[]
  references: string[]
}

export interface ExtractionResult {
  document_id: string
  backend: string
  prompt_version: string | null
  model: string | null
  latency_ms: number
  warnings: string[]
  norm: LegalNorm
}

export interface FieldScore {
  field: string
  precision: number
  recall: number
  f1: number
  support: number
  predicted: number
}

export interface EvalReport {
  n_documents: number
  backend: string
  prompt_version: string | null
  macro_f1: number
  micro_f1: number
  field_scores: FieldScore[]
  retrieval: Record<string, number>
}

export interface EvaluationResponse {
  report: EvalReport
  per_document: { source: string; macro_f1: number; weakest_fields: string[] }[]
  markdown: string
}

export interface Stats {
  documents: number
  chunks: number
  vocab_size: number
  characters: number
}
