import type { Session } from '@supabase/supabase-js'
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

/** Shared showcase account. Its data is intentionally non-sensitive and resettable. */
export async function signInAsDemo(): Promise<void> {
  await signInWithPassword('demo@plotplanner.app', 'PlotPlannerDemo!2026')
}

export async function sendPasswordReset(email: string): Promise<void> {
  const { error } = await getSupabase().auth.resetPasswordForEmail(email, {
    redirectTo: `${window.location.origin}/reset-password`,
  })
  if (error) throw error
}

export async function updatePassword(password: string): Promise<void> {
  const { error } = await getSupabase().auth.updateUser({ password })
  if (error) throw error
}

export async function signOut(): Promise<void> {
  const { error } = await getSupabase().auth.signOut()
  if (error) throw error
}

export async function getAccessToken(): Promise<string | null> {
  return (await getSession())?.access_token ?? null
}
