import { useRef, useState } from 'react'
import type { DocumentSummary } from '../types'

interface Props {
  documents: DocumentSummary[]
  selectedId: string | null
  onSelect: (id: string) => void
  onUpload: (file: File) => Promise<void>
  onIngestText: (text: string) => Promise<void>
  onLoadCorpus: () => Promise<void>
  onRemove: (id: string) => Promise<void>
}

export function DocumentsPanel({
  documents,
  selectedId,
  onSelect,
  onUpload,
  onIngestText,
  onLoadCorpus,
  onRemove,
}: Props) {
  const [text, setText] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)

  return (
    <section className="panel">
      <h2>1. Documentos</h2>
      <div className="row">
        <button type="button" onClick={onLoadCorpus}>
          Carregar corpus de exemplo
        </button>
        <button type="button" onClick={() => fileInput.current?.click()}>
          Enviar arquivo (.txt/.md/.pdf)
        </button>
        <input
          ref={fileInput}
          type="file"
          accept=".txt,.md,.pdf"
          aria-label="Arquivo da norma"
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) void onUpload(file)
            event.target.value = ''
          }}
        />
      </div>

      <form
        className="stack"
        onSubmit={(event) => {
          event.preventDefault()
          if (text.trim().length >= 20) {
            void onIngestText(text).then(() => setText(''))
          }
        }}
      >
        <label htmlFor="texto-norma">Colar texto da norma</label>
        <textarea
          id="texto-norma"
          rows={4}
          value={text}
          placeholder="LEI Nº 1.234, DE 1º DE JANEIRO DE 2024..."
          onChange={(event) => setText(event.target.value)}
        />
        <button type="submit" disabled={text.trim().length < 20}>
          Ingerir texto
        </button>
      </form>

      <ul className="doc-list">
        {documents.map((doc) => (
          <li key={doc.id} className={doc.id === selectedId ? 'doc selected' : 'doc'}>
            <button type="button" className="doc-main" onClick={() => onSelect(doc.id)}>
              <strong>{doc.source}</strong>
              <span>
                {doc.n_chunks} chunks · {doc.n_chars.toLocaleString('pt-BR')} caracteres
              </span>
            </button>
            <button
              type="button"
              className="danger"
              aria-label={`Remover ${doc.source}`}
              onClick={() => void onRemove(doc.id)}
            >
              ×
            </button>
          </li>
        ))}
        {documents.length === 0 && <li className="empty">Nenhum documento indexado ainda.</li>}
      </ul>
    </section>
  )
}
