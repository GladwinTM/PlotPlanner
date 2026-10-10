import { describe, expect, it } from 'vitest'
import { ConfigError, parseEnv } from './env'

const valid = {
  VITE_API_BASE_URL: 'http://localhost:8000/api/v1/',
  VITE_SUPABASE_URL: 'https://abc.supabase.co',
  VITE_SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_abc',
}

describe('parseEnv', () => {
  it('returns normalized public configuration', () => {
    expect(parseEnv(valid)).toEqual({
      apiBaseUrl: 'http://localhost:8000/api/v1',
      supabaseUrl: 'https://abc.supabase.co',
      supabasePublishableKey: 'sb_publishable_abc',
    })
  })

  it.each(['VITE_API_BASE_URL', 'VITE_SUPABASE_URL', 'VITE_SUPABASE_PUBLISHABLE_KEY'])('requires %s', (name) => {
    expect(() => parseEnv({ ...valid, [name]: undefined })).toThrow(ConfigError)
    expect(() => parseEnv({ ...valid, [name]: undefined })).toThrow(name)
  })

  it('rejects template placeholders', () => {
    expect(() => parseEnv({ ...valid, VITE_SUPABASE_URL: 'https://YOUR_PROJECT.supabase.co' })).toThrow(/placeholder/)
    expect(() => parseEnv({ ...valid, VITE_SUPABASE_PUBLISHABLE_KEY: 'YOUR_PUBLISHABLE_KEY' })).toThrow(/placeholder/)
  })

  it('refuses a secret key in a browser-visible variable without echoing it', () => {
    const secret = 'sb_secret_do_not_leak'
    let message = ''
    try {
      parseEnv({ ...valid, VITE_SUPABASE_PUBLISHABLE_KEY: secret })
    } catch (error) {
      message = (error as Error).message
    }
    expect(message).toMatch(/secret key/)
    expect(message).not.toContain(secret)
  })
})
