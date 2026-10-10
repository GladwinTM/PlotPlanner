/**
 * Public, browser-safe configuration. Every value here is embedded in the
 * bundle, which is why only VITE_-prefixed variables are read and why secrets
 * (LLM, YouTube, database, service-role keys) must never appear in them.
 */
export class ConfigError extends Error {}

export type AppEnv = {
  apiBaseUrl: string
  supabaseUrl: string
  supabasePublishableKey: string
}

type RawEnv = Record<string, string | undefined>

const PLACEHOLDER = /YOUR_/i

function required(raw: RawEnv, name: string): string {
  const value = raw[name]?.trim()
  if (!value) throw new ConfigError(`${name} is not set. Copy frontend/.env.example to frontend/.env.`)
  if (PLACEHOLDER.test(value)) throw new ConfigError(`${name} still contains template placeholder text.`)
  return value
}

export function parseEnv(raw: RawEnv): AppEnv {
  const apiBaseUrl = required(raw, 'VITE_API_BASE_URL').replace(/\/+$/, '')
  const supabaseUrl = required(raw, 'VITE_SUPABASE_URL').replace(/\/+$/, '')
  const supabasePublishableKey = required(raw, 'VITE_SUPABASE_PUBLISHABLE_KEY')

  // Guard against pasting a privileged key into a browser-visible variable.
  if (supabasePublishableKey.startsWith('sb_secret_')) {
    throw new ConfigError('VITE_SUPABASE_PUBLISHABLE_KEY contains a secret key. Use the publishable key.')
  }
  return { apiBaseUrl, supabaseUrl, supabasePublishableKey }
}

let cached: AppEnv | undefined

export function getEnv(): AppEnv {
  cached ??= parseEnv(import.meta.env as RawEnv)
  return cached
}
