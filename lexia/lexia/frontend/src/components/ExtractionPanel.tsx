import type { ExtractionResult } from '../types'

interface Props {
  documentLabel: string | null
  result: ExtractionResult | null
  loading: boolean
  onExtract: () => Promise<void>
}

export function ExtractionPanel({ documentLabel, result, loading, onExtract }: Props) {
  const norm = result?.norm
  return (
    <section className="panel">
      <h2>3. Extração estruturada</h2>
      <div className="row">
        <span className="muted">
          {documentLabel ? `Documento: ${documentLabel}` : 'Selecione um documento na lista.'}
        </span>
        <button type="button" disabled={!documentLabel || loading} onClick={() => void onExtract()}>
          {loading ? 'Extraindo...' : 'Extrair campos'}
        </button>
      </div>

      {result && norm && (
        <>
          <p className="muted">
            backend <strong>{result.backend}</strong>
            {result.prompt_version ? ` · prompt ${result.prompt_version}` : ''}
            {result.model ? ` · ${result.model}` : ''} · {result.latency_ms.toFixed(1)} ms
          </p>
          {result.warnings.map((warning) => (
            <p key={warning} className="warning">
              {warning}
            </p>
          ))}
          <dl className="fields">
            <dt>Tipo</dt>
            <dd>{norm.norm_type}</dd>
            <dt>Número/ano</dt>
            <dd>
              {norm.number ?? '—'}/{norm.year ?? '—'}
            </dd>
            <dt>Órgão</dt>
            <dd>{norm.issuing_body ?? '—'}</dd>
            <dt>Publicação</dt>
            <dd>{norm.publication_date ?? '—'}</dd>
            <dt>Vigência</dt>
            <dd>{norm.effective_date ?? '—'}</dd>
            <dt>Ementa</dt>
            <dd>{norm.subject ?? '—'}</dd>
          </dl>

          <h3>Obrigações ({norm.obligations.length})</h3>
          <ul className="items">
            {norm.obligations.map((item, index) => (
              <li key={`${item.article}-${index}`}>
                <span className="tag">{item.article ?? '—'}</span> <strong>{item.subject}</strong>{' '}
                {item.action}
              </li>
            ))}
          </ul>

          <h3>Prazos ({norm.deadlines.length})</h3>
          <ul className="items">
            {norm.deadlines.map((item, index) => (
              <li key={`${item.article}-${index}`}>
                <span className="tag">{item.article ?? '—'}</span>{' '}
                <strong>
                  {item.value ?? '?'} {item.unit ?? ''}
                </strong>{' '}
                — {item.description}
              </li>
            ))}
          </ul>

          <h3>Penalidades ({norm.penalties.length})</h3>
          <ul className="items">
            {norm.penalties.map((item, index) => (
              <li key={`${item.article}-${index}`}>
                <span className="tag">{item.article ?? '—'}</span> {item.kind}
                {item.amount ? ` — ${item.amount}` : ''}
              </li>
            ))}
          </ul>

          <h3>Normas citadas ({norm.references.length})</h3>
          <p>{norm.references.join(' · ') || '—'}</p>

          <details>
            <summary>JSON completo</summary>
            <pre>{JSON.stringify(norm, null, 2)}</pre>
          </details>
        </>
      )}
    </section>
  )
}
