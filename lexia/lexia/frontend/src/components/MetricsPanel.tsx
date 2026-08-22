import type { EvaluationResponse } from '../types'

interface Props {
  evaluation: EvaluationResponse | null
  loading: boolean
  onEvaluate: () => Promise<void>
}

export function MetricsPanel({ evaluation, loading, onEvaluate }: Props) {
  const report = evaluation?.report
  return (
    <section className="panel">
      <h2>4. Métricas de qualidade</h2>
      <div className="row">
        <span className="muted">
          Compara a extração com o golden set anotado (<code>data/eval/golden.json</code>).
        </span>
        <button type="button" disabled={loading} onClick={() => void onEvaluate()}>
          {loading ? 'Avaliando...' : 'Rodar avaliação'}
        </button>
      </div>

      {report && (
        <>
          <div className="kpis">
            <div>
              <span>Macro-F1</span>
              <strong>{report.macro_f1.toFixed(3)}</strong>
            </div>
            <div>
              <span>Micro-F1</span>
              <strong>{report.micro_f1.toFixed(3)}</strong>
            </div>
            <div>
              <span>Recall@5</span>
              <strong>{(report.retrieval['recall@5'] ?? 0).toFixed(3)}</strong>
            </div>
            <div>
              <span>MRR</span>
              <strong>{(report.retrieval.mrr ?? 0).toFixed(3)}</strong>
            </div>
            <div>
              <span>Documentos</span>
              <strong>{report.n_documents}</strong>
            </div>
          </div>

          <table>
            <caption>F1 por campo — backend {report.backend}</caption>
            <thead>
              <tr>
                <th>Campo</th>
                <th>Precisão</th>
                <th>Recall</th>
                <th>F1</th>
                <th>Suporte</th>
              </tr>
            </thead>
            <tbody>
              {report.field_scores.map((field) => (
                <tr key={field.field} className={field.f1 < 0.9 ? 'low' : undefined}>
                  <td>{field.field}</td>
                  <td>{field.precision.toFixed(3)}</td>
                  <td>{field.recall.toFixed(3)}</td>
                  <td>{field.f1.toFixed(3)}</td>
                  <td>{field.support}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  )
}
