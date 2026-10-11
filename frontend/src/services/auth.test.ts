import { afterEach, describe, expect, it, vi } from 'vitest'

const signInWithPassword = vi.fn()
const resetPasswordForEmail = vi.fn()
const updateUser = vi.fn()
vi.mock('../lib/supabase', () => ({ getSupabase: () => ({ auth: { signInWithPassword, resetPasswordForEmail, updateUser } }) }))

import { sendPasswordReset, signInAsDemo, updatePassword } from './auth'

afterEach(() => { vi.resetAllMocks() })

describe('email authentication helpers', () => {
  it('signs in to the shared demo workspace with its fixed demo credentials', async () => {
    signInWithPassword.mockResolvedValue({ error: null })
    await signInAsDemo()
    expect(signInWithPassword).toHaveBeenCalledWith({ email: 'demo@plotplanner.app', password: 'PlotPlannerDemo!2026' })
  })

  it('requests a reset link to the dedicated reset route', async () => {
    resetPasswordForEmail.mockResolvedValue({ error: null })
    await sendPasswordReset('ada@example.com')
    expect(resetPasswordForEmail).toHaveBeenCalledWith('ada@example.com', { redirectTo: `${window.location.origin}/reset-password` })
  })

  it('updates the recovered user password', async () => {
    updateUser.mockResolvedValue({ error: null })
    await updatePassword('new-password')
    expect(updateUser).toHaveBeenCalledWith({ password: 'new-password' })
  })
})
