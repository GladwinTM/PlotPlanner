import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./auth', () => ({ getAccessToken: vi.fn() }))
vi.mock('../lib/env', () => ({ getEnv: () => ({ apiBaseUrl: 'http://api.test/api/v1' }) }))

import { ApiError, getProfile, updateProfile } from './api'
import { getAccessToken } from './auth'

const fetchMock = vi.fn()

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  vi.mocked(getAccessToken).mockResolvedValue('token-123')
})

afterEach(() => {
  fetchMock.mockReset()
  vi.unstubAllGlobals()
})

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('api client', () => {
  it('sends the access token as a bearer header to the configured base URL', async () => {
    fetchMock.mockResolvedValue(json({ user_id: 'u1' }))

    await getProfile()

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('http://api.test/api/v1/profile')
    expect(init.headers.Authorization).toBe('Bearer token-123')
  })

  it('sends only the provided fields on update', async () => {
    fetchMock.mockResolvedValue(json({ user_id: 'u1' }))

    await updateProfile({ location: 'Pune' })

    const [, init] = fetchMock.mock.calls[0]
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body)).toEqual({ location: 'Pune' })
  })

  it('does not call the API when signed out', async () => {
    vi.mocked(getAccessToken).mockResolvedValue(null)

    await expect(getProfile()).rejects.toMatchObject({ status: 401, code: 'authentication_required' })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('maps the backend error envelope to ApiError', async () => {
    fetchMock.mockResolvedValue(json({ error: { code: 'token_expired', message: 'Access token has expired' } }, 401))

    const error = await getProfile().catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 401, code: 'token_expired', message: 'Access token has expired' })
  })

  it('reports an unreachable backend clearly', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(getProfile()).rejects.toMatchObject({ code: 'network_error' })
  })

  it('falls back to the status text for non-JSON errors', async () => {
    fetchMock.mockResolvedValue(new Response('<html>bad gateway</html>', { status: 502, statusText: 'Bad Gateway' }))

    await expect(getProfile()).rejects.toMatchObject({ status: 502, message: 'Bad Gateway' })
  })
})
