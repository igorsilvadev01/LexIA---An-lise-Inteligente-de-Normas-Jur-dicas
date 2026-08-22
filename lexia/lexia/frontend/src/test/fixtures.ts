import type {
  DocumentSummary,
  EvaluationResponse,
  ExtractionResult,
  SearchHit,
  Stats,
} from '../types'

export const stats: Stats = { documents: 2, chunks: 24, vocab_size: 812, characters: 9100 }

export const documents: DocumentSummary[] = [
  { id: 'lei-4444#a1', title: 'PRESIDÊNCIA DA REPÚBLICA', source: 'lei-4444-2021.txt', n_chunks: 12, n_chars: 4200 },
  { id: 'portaria-45#b2', title: 'MINISTÉRIO DA GESTÃO', source: 'portaria-45-2024.txt', n_chunks: 8, n_chars: 2100 },
]

export const hits: SearchHit[] = [
  {
    chunk_id: 'lei-4444#a1-0',
    document_id: 'lei-4444#a1',
    document_title: 'PRESIDÊNCIA DA REPÚBLICA',
    text: 'Art. 4º O controlador deverá responder ao pedido de acesso em até 15 (quinze) dias.',
    score: 0.0328,
    lexical_score: 7.412,
    semantic_score: 0.311,
    article: 'Art. 4º',
  },
]

export const extraction: ExtractionResult = {
  document_id: 'lei-4444#a1',
  backend: 'rules',
  prompt_version: null,
  model: null,
  latency_ms: 3.5,
  warnings: [],
  norm: {
    norm_type: 'lei',
    number: '4.444',
    year: 2021,
    issuing_body: 'PRESIDÊNCIA DA REPÚBLICA',
    publication_date: '2021-03-12',
    effective_date: '2021-06-10',
    subject: 'Dispõe sobre a transparência de dados públicos.',
    obligations: [
      {
        subject: 'o controlador',
        action: 'deverá responder ao pedido de acesso',
        article: 'Art. 4º',
        evidence: 'Art. 4º O controlador deverá responder...',
      },
    ],
    deadlines: [
      { description: 'responder ao pedido de acesso', value: 15, unit: 'dias', article: 'Art. 4º' },
    ],
    penalties: [{ kind: 'multa', amount: 'R$ 50.000.000,00', article: 'Art. 8º' }],
    references: ['Lei nº 13.709/2018'],
  },
}

export const evaluation: EvaluationResponse = {
  report: {
    n_documents: 5,
    backend: 'rules',
    prompt_version: null,
    macro_f1: 0.972,
    micro_f1: 0.943,
    field_scores: [
      { field: 'publication_date', precision: 1, recall: 1, f1: 1, support: 5, predicted: 5 },
      { field: 'obligations', precision: 1, recall: 0.62, f1: 0.765, support: 13, predicted: 8 },
    ],
    retrieval: { 'recall@1': 0.8333, 'recall@5': 1, mrr: 0.9028 },
  },
  per_document: [{ source: 'portaria-45-2024.txt', macro_f1: 0.88, weakest_fields: ['obligations'] }],
  markdown: '# Relatório de avaliação',
}
