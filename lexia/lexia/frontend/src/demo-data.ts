import type { DocumentSummary, EvaluationResponse, ExtractionResult, SearchHit, Stats } from './types'

export const demoDocuments: DocumentSummary[] = [
  { id: 'lei-13709#lgpd', title: 'LEI GERAL DE PROTEÇÃO DE DADOS', source: 'lei-13.709-2018.txt', n_chunks: 34, n_chars: 18420 },
  { id: 'resolucao-cd-anpd-2', title: 'AUTORIDADE NACIONAL DE PROTEÇÃO DE DADOS', source: 'resolucao-cd-anpd-2-2022.txt', n_chunks: 18, n_chars: 9730 },
  { id: 'portaria-45#demo', title: 'MINISTÉRIO DA GESTÃO', source: 'portaria-45-2024.txt', n_chunks: 8, n_chars: 4210 },
]

export const demoStats = (documents = demoDocuments): Stats => ({
  documents: documents.length,
  chunks: documents.reduce((total, item) => total + item.n_chunks, 0),
  vocab_size: 2814,
  characters: documents.reduce((total, item) => total + item.n_chars, 0),
})

export const demoHits: SearchHit[] = [
  { chunk_id: 'lei-13709#lgpd-21', document_id: 'lei-13709#lgpd', document_title: 'LEI GERAL DE PROTEÇÃO DE DADOS', text: 'O titular tem direito a obter do controlador, em relação aos dados por ele tratados, a qualquer momento e mediante requisição.', score: 0.0389, lexical_score: 8.412, semantic_score: 0.781, article: 'Art. 18' },
  { chunk_id: 'resolucao-cd-anpd-2-4', document_id: 'resolucao-cd-anpd-2', document_title: 'AUTORIDADE NACIONAL DE PROTEÇÃO DE DADOS', text: 'O agente de tratamento de pequeno porte atenderá às solicitações dos titulares conforme os prazos definidos na regulamentação.', score: 0.0312, lexical_score: 6.911, semantic_score: 0.704, article: 'Art. 14' },
]

export const demoExtraction: ExtractionResult = {
  document_id: 'lei-13709#lgpd', backend: 'rules', prompt_version: null, model: null, latency_ms: 4.8, warnings: [],
  norm: {
    norm_type: 'lei', number: '13.709', year: 2018, issuing_body: 'PRESIDÊNCIA DA REPÚBLICA',
    publication_date: '2018-08-15', effective_date: '2020-09-18',
    subject: 'Proteção de dados pessoais, inclusive nos meios digitais.',
    obligations: [{ subject: 'o controlador', action: 'comunicar incidentes de segurança à autoridade nacional e ao titular', article: 'Art. 48', evidence: 'O controlador deverá comunicar à autoridade nacional e ao titular a ocorrência de incidente de segurança.' }],
    deadlines: [{ description: 'fornecimento de declaração clara e completa', value: 15, unit: 'dias', article: 'Art. 19, II' }],
    penalties: [{ kind: 'multa simples', amount: 'até 2% do faturamento, limitada a R$ 50.000.000,00', article: 'Art. 52, II' }],
    references: ['Constituição Federal', 'Marco Civil da Internet'],
  },
}

export const demoEvaluation: EvaluationResponse = {
  report: {
    n_documents: 5, backend: 'rules', prompt_version: null, macro_f1: 0.972, micro_f1: 0.943,
    field_scores: [
      { field: 'publication_date', precision: 1, recall: 1, f1: 1, support: 5, predicted: 5 },
      { field: 'obligations', precision: 1, recall: 0.62, f1: 0.765, support: 13, predicted: 8 },
      { field: 'deadlines', precision: 1, recall: 1, f1: 1, support: 7, predicted: 7 },
    ],
    retrieval: { 'recall@1': 0.8333, 'recall@5': 1, mrr: 0.9028 },
  },
  per_document: [{ source: 'portaria-45-2024.txt', macro_f1: 0.88, weakest_fields: ['obligations'] }],
  markdown: '# Relatório de avaliação',
}
