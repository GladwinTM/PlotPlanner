import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./services/auth')
// Keep the real ApiError class; only the network-calling functions are replaced.
vi.mock('./services/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./services/api')>()),
  getProfile: vi.fn(),
  updateProfile: vi.fn(),
}))

import App from './App'
import { ApiError, getProfile, updateProfile } from './services/api'
import * as auth from './services/auth'
import { fakeSession, renderApp } from './test/render'
import type { Profile } from './types/profile'

const profile: Profile = {
  user_id: 'user-1',
  display_name: 'Ada',
  location: null,
  current_occupation: 'Engineer',
  education_summary: null,
  experience_summary: null,
  available_hours_per_week: null,
  learning_preferences: null,
  constraints_summary: null,
  onboarding_completed: true,
  created_at: '2026-10-11T00:00:00Z',
  updated_at: '2026-10-11T00:00:00Z',
}

function signedIn(signedIn: boolean) {
  vi.mocked(auth.getSession).mockResolvedValue(signedIn ? fakeSession() : null)
  vi.mocked(auth.onAuthChange).mockReturnValue(() => {})
}

beforeEach(() => {
  vi.resetAllMocks()
})

describe('protected routes', () => {
  it('sends a signed-out visitor to the login page and never calls the API', async () => {
    signedIn(false)

    renderApp(<App />, { route: '/settings' })

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(getProfile).not.toHaveBeenCalled()
  })

  it('shows the profile page to a signed-in user', async () => {
    signedIn(true)
    vi.mocked(getProfile).mockResolvedValue(profile)

    renderApp(<App />, { route: '/settings' })

    expect(await screen.findByLabelText('Display name')).toHaveValue('Ada')
    expect(screen.getByText('ada@example.com')).toBeInTheDocument()
  })

  it('redirects a signed-in user away from the login page', async () => {
    signedIn(true)
    vi.mocked(getProfile).mockResolvedValue(profile)

    renderApp(<App />, { route: '/login' })

    expect(await screen.findByRole('heading', { name: /welcome back, ada/i })).toBeInTheDocument()
  })

  it('signs out through the auth service', async () => {
    signedIn(true)
    vi.mocked(getProfile).mockResolvedValue(profile)
    vi.mocked(auth.signOut).mockResolvedValue()

    renderApp(<App />, { route: '/settings' })
    await userEvent.click(await screen.findByRole('button', { name: 'Sign out' }))

    expect(auth.signOut).toHaveBeenCalledOnce()
  })
})

describe('login', () => {
  it('signs in with the entered credentials', async () => {
    signedIn(false)
    vi.mocked(auth.signInWithPassword).mockResolvedValue()
    renderApp(<App />, { route: '/login' })

    await userEvent.type(await screen.findByLabelText('Email'), ' ada@example.com ')
    await userEvent.type(screen.getByLabelText('Password'), 'correct horse')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(auth.signInWithPassword).toHaveBeenCalledWith('ada@example.com', 'correct horse')
  })

  it('shows the real error when sign in fails', async () => {
    signedIn(false)
    vi.mocked(auth.signInWithPassword).mockRejectedValue(new Error('Invalid login credentials'))
    renderApp(<App />, { route: '/login' })

    await userEvent.type(await screen.findByLabelText('Email'), 'ada@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'wrong-password')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid login credentials')
  })

  it('tells a new user to confirm their email', async () => {
    signedIn(false)
    vi.mocked(auth.signUpWithPassword).mockResolvedValue({ needsEmailConfirmation: true })
    renderApp(<App />, { route: '/login' })

    await userEvent.click(await screen.findByRole('button', { name: /create an account/i }))
    await userEvent.type(screen.getByLabelText('Email'), 'new@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'long-enough')
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByText(/confirmation link to new@example.com/)).toBeInTheDocument()
  })

  it('surfaces a provider error instead of failing silently when Google is unavailable', async () => {
    signedIn(false)
    vi.mocked(auth.signInWithGoogle).mockRejectedValue(new Error('Unsupported provider: provider is not enabled'))
    renderApp(<App />, { route: '/login' })

    await userEvent.click(await screen.findByRole('button', { name: 'Continue with Google' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('provider is not enabled')
  })
})

describe('profile settings', () => {
  it('saves edits and confirms them', async () => {
    signedIn(true)
    vi.mocked(getProfile).mockResolvedValue(profile)
    vi.mocked(updateProfile).mockResolvedValue({ ...profile, display_name: 'Ada L.', location: 'London' })
    renderApp(<App />, { route: '/settings' })

    const name = await screen.findByLabelText('Display name')
    await userEvent.clear(name)
    await userEvent.type(name, 'Ada L.')
    await userEvent.type(screen.getByLabelText('Location'), 'London')
    await userEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(await screen.findByText('Profile saved.')).toBeInTheDocument()
    expect(updateProfile).toHaveBeenCalledWith(
      expect.objectContaining({ display_name: 'Ada L.', location: 'London', current_occupation: 'Engineer' }),
    )
    expect(vi.mocked(updateProfile).mock.calls[0][0]).not.toHaveProperty('user_id')
  })

  it('shows the server message when saving fails', async () => {
    signedIn(true)
    vi.mocked(getProfile).mockResolvedValue(profile)
    vi.mocked(updateProfile).mockRejectedValue(new ApiError(422, 'validation_error', 'Request validation failed'))
    renderApp(<App />, { route: '/settings' })

    await userEvent.click(await screen.findByRole('button', { name: 'Save changes' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Request validation failed')
    expect(screen.queryByText('Profile saved.')).not.toBeInTheDocument()
  })

  it('shows a load error with a retry that works', async () => {
    signedIn(true)
    vi.mocked(getProfile)
      .mockRejectedValueOnce(new ApiError(0, 'network_error', 'Cannot reach the PlotPlanner API'))
      .mockResolvedValue(profile)
    renderApp(<App />, { route: '/settings' })

    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the PlotPlanner API')
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))

    await waitFor(() => expect(screen.getByLabelText('Display name')).toHaveValue('Ada'))
  })
})
