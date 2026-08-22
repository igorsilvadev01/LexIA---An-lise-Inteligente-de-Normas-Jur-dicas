import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api } from './api'
import { documents, hits } from './test/fixtures'

function mockFetch(body: unknown, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: status < 400,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => vi.unstubAllGlobals())

describe('api', () => {
  it('envia JSON com content-type na busca', async () => {
    const fetchMock = mockFetch({ query: 'prazo', hits })
    const response = await api.search('prazo', 3)

    expect(response.hits[0].article).toBe('Art. 4º')
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toContain('/api/search')
    expect(init.method).toBe('POST')
    expect(init.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(init.body)).toEqual({ query: 'prazo', top_k: 3, document_id: null })
  })

  it('propaga document_id quando a busca é restrita', async () => {
    const fetchMock = mockFetch({ query: 'prazo', hits })
    await api.search('prazo', 5, 'lei-4444#a1')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).document_id).toBe('lei-4444#a1')
  })

  it('não força content-type em upload multipart', async () => {
    const fetchMock = mockFetch(documents[0])
    await api.upload(new File(['conteudo'], 'norma.txt', { type: 'text/plain' }))

    const init = fetchMock.mock.calls[0][1]
    expect(init.body).toBeInstanceOf(FormData)
    expect(init.headers).toBeUndefined()
  })

  it('trata 204 sem corpo na remoção', async () => {
    mockFetch(null, 204)
    await expect(api.remove('lei-4444#a1')).resolves.toBeUndefined()
  })

  it('lança ApiError com status em falhas HTTP', async () => {
    mockFetch({ detail: 'documento não encontrado' }, 404)
    await expect(api.extract('inexistente')).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
    })
    expect(new ApiError('x', 500)).toBeInstanceOf(Error)
  })
})
