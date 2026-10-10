import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const signInWithOAuth = vi.fn()
vi.mock('../lib/supabase', () => ({ getSupabase: () => ({ auth: { signInWithOAuth } }) }))
vi.mock('../lib/env', () => ({
  getEnv: () => ({ supabaseUrl: 'https://proj.supabase.co', supabasePublishableKey: 'sb_publishable_x' }),
}))

import { signInWithGoogle } from './auth'

const fetchMock = vi.fn()

function settings(google: boolean) {
  return new Response(JSON.stringify({ external: { google, email: true } }), { status: 200 })
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  signInWithOAuth.mockResolvedValue({ error: null })
})

afterEach(() => {
  fetchMock.mockReset()
  signInWithOAuth.mockReset()
  vi.unstubAllGlobals()
})

describe('signInWithGoogle', () => {
  it('explains a disabled provider and never redirects the page', async () => {
    fetchMock.mockResolvedValue(settings(false))

    await expect(signInWithGoogle()).rejects.toThrow(/not enabled/)
    expect(signInWithOAuth).not.toHaveBeenCalled()
    expect(fetchMock).toHaveBeenCalledWith(
      'https://proj.supabase.co/auth/v1/settings',
      expect.objectContaining({ headers: { apikey: 'sb_publishable_x' } }),
    )
  })

  it('starts the OAuth flow when the provider is enabled', async () => {
    fetchMock.mockResolvedValue(settings(true))

    await signInWithGoogle()

    expect(signInWithOAuth).toHaveBeenCalledWith(expect.objectContaining({ provider: 'google' }))
  })

  it('reports a settings lookup failure instead of guessing', async () => {
    fetchMock.mockResolvedValue(new Response('nope', { status: 502 }))

    await expect(signInWithGoogle()).rejects.toThrow(/HTTP 502/)
    expect(signInWithOAuth).not.toHaveBeenCalled()
  })
})
