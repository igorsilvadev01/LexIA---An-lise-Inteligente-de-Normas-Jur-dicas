import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { api } from './api'
import { documents, evaluation, extraction, hits, stats } from './test/fixtures'

function stubApi() {
  vi.spyOn(api, 'documents').mockResolvedValue(documents)
  vi.spyOn(api, 'stats').mockResolvedValue(stats)
  vi.spyOn(api, 'search').mockResolvedValue({ query: 'prazo', hits })
  vi.spyOn(api, 'extract').mockResolvedValue(extraction)
  vi.spyOn(api, 'evaluate').mockResolvedValue(evaluation)
  vi.spyOn(api, 'loadCorpus').mockResolvedValue({ loaded: 5, documents })
  vi.spyOn(api, 'upload').mockResolvedValue(documents[0])
  vi.spyOn(api, 'ingestText').mockResolvedValue(documents[0])
  vi.spyOn(api, 'remove').mockResolvedValue(undefined)
}

beforeEach(stubApi)
afterEach(() => vi.restoreAllMocks())

describe('App', () => {
  it('mostra estatísticas e documentos carregados', async () => {
    render(<App />)
    expect(await screen.findByText('lei-4444-2021.txt')).toBeInTheDocument()
    expect(screen.getByText('24')).toBeInTheDocument()
    expect(screen.getByText(/12 chunks/)).toBeInTheDocument()
  })

  it('busca e exibe trechos com artigo e scores', async () => {
    render(<App />)
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('Consulta'), 'prazo de acesso')
    await user.click(screen.getByRole('button', { name: 'Buscar' }))

    expect(await screen.findByText(/O controlador deverá responder/)).toBeInTheDocument()
    expect(screen.getByText('Art. 4º')).toBeInTheDocument()
    expect(screen.getByText(/RRF 0.0328/)).toBeInTheDocument()
    expect(api.search).toHaveBeenCalledWith('prazo de acesso', 5, undefined)
  })

  it('usa consulta sugerida ao clicar no chip', async () => {
    render(<App />)
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: /multa sobre o faturamento/ }))
    await waitFor(() =>
      expect(api.search).toHaveBeenCalledWith(
        'multa sobre o faturamento anual da plataforma',
        5,
        undefined,
      ),
    )
  })

  it('restringe a busca ao documento selecionado', async () => {
    render(<App />)
    const user = userEvent.setup()

    await user.click(await screen.findByText('lei-4444-2021.txt'))
    await user.click(screen.getByRole('checkbox'))
    await user.type(screen.getByLabelText('Consulta'), 'prazo')
    await user.click(screen.getByRole('button', { name: 'Buscar' }))

    expect(api.search).toHaveBeenCalledWith('prazo', 5, 'lei-4444#a1')
  })

  it('extrai campos estruturados do documento selecionado', async () => {
    render(<App />)
    const user = userEvent.setup()

    expect(screen.getByRole('button', { name: 'Extrair campos' })).toBeDisabled()
    await user.click(await screen.findByText('lei-4444-2021.txt'))
    await user.click(screen.getByRole('button', { name: 'Extrair campos' }))

    expect(await screen.findByText('4.444/2021')).toBeInTheDocument()
    expect(screen.getByText('2021-03-12')).toBeInTheDocument()
    expect(screen.getByText('Obrigações (1)')).toBeInTheDocument()
    expect(screen.getByText(/15 dias/)).toBeInTheDocument()
    expect(screen.getByText('Penalidades (1)')).toBeInTheDocument()
    expect(screen.getAllByText(/R\$ 50.000.000,00/).length).toBeGreaterThan(0)
    expect(screen.getByText(/backend/)).toHaveTextContent('rules')
  })

  it('mostra métricas de avaliação e destaca campo fraco', async () => {
    render(<App />)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Rodar avaliação' }))

    expect(await screen.findByText('0.972')).toBeInTheDocument()
    expect(screen.getByText('0.903')).toBeInTheDocument()
    const linha = screen.getByRole('row', { name: /obligations/ })
    expect(linha).toHaveClass('low')
    expect(within(linha).getByText('0.765')).toBeInTheDocument()
  })

  it('ingere texto colado e seleciona o documento resultante', async () => {
    render(<App />)
    const user = userEvent.setup()

    const textarea = await screen.findByLabelText('Colar texto da norma')
    expect(screen.getByRole('button', { name: 'Ingerir texto' })).toBeDisabled()
    await user.type(textarea, 'LEI Nº 1.234, DE 1º DE JANEIRO DE 2024. Art. 1º Teste.')
    await user.click(screen.getByRole('button', { name: 'Ingerir texto' }))

    await waitFor(() => expect(api.ingestText).toHaveBeenCalled())
    expect(await screen.findByText(/Documento: lei-4444-2021.txt/)).toBeInTheDocument()
  })

  it('carrega corpus de exemplo e remove documento', async () => {
    render(<App />)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /Carregar corpus/ }))
    expect(api.loadCorpus).toHaveBeenCalled()

    await user.click(screen.getByLabelText('Remover portaria-45-2024.txt'))
    expect(api.remove).toHaveBeenCalledWith('portaria-45#b2')
  })

  it('exibe erro quando a API falha', async () => {
    vi.spyOn(api, 'evaluate').mockRejectedValue(new Error('backend indisponível'))
    render(<App />)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Rodar avaliação' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('backend indisponível')
  })
})
