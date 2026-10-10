import type { Session } from '@supabase/supabase-js'
import { getEnv } from '../lib/env'
import { getSupabase } from '../lib/supabase'

export type { Session }

export type SignUpResult = { needsEmailConfirmation: boolean }

export async function getSession(): Promise<Session | null> {
  const { data, error } = await getSupabase().auth.getSession()
  if (error) throw error
  return data.session
}

/** Subscribe to sign-in, sign-out and token refresh. Returns an unsubscribe function. */
export function onAuthChange(callback: (session: Session | null) => void): () => void {
  const { data } = getSupabase().auth.onAuthStateChange((_event, session) => callback(session))
  return () => data.subscription.unsubscribe()
}

export async function signInWithPassword(email: string, password: string): Promise<void> {
  const { error } = await getSupabase().auth.signInWithPassword({ email, password })
  if (error) throw error
}

export async function signUpWithPassword(email: string, password: string): Promise<SignUpResult> {
  const { data, error } = await getSupabase().auth.signUp({
    email,
    password,
    options: { emailRedirectTo: window.location.origin },
  })
  if (error) throw error
  return { needsEmailConfirmation: data.session === null }
}

/** Public project auth settings: tells us which providers are enabled. */
async function isGoogleEnabled(): Promise<boolean> {
  const { supabaseUrl, supabasePublishableKey } = getEnv()
  const response = await fetch(`${supabaseUrl}/auth/v1/settings`, { headers: { apikey: supabasePublishableKey } })
  if (!response.ok) throw new Error(`Could not read the sign-in settings (HTTP ${response.status}).`)
  const settings = (await response.json()) as { external?: { google?: boolean } }
  return settings.external?.google === true
}

export async function signInWithGoogle(): Promise<void> {
  // supabase-js redirects the whole page immediately, so a disabled provider
  // would land the user on a raw JSON error. Check first and explain instead.
  if (!(await isGoogleEnabled())) {
    throw new Error('Google sign-in is not enabled for this project yet. Use email and password for now.')
  }
  const { error } = await getSupabase().auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: window.location.origin },
  })
  if (error) throw error
}

export async function signOut(): Promise<void> {
  const { error } = await getSupabase().auth.signOut()
  if (error) throw error
}

export async function getAccessToken(): Promise<string | null> {
  return (await getSession())?.access_token ?? null
}
