import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../app/AuthProvider'
import * as auth from '../services/auth'

type Mode = 'signin' | 'signup'

export function LoginPage() {
  const { session, loading } = useAuth()
  const location = useLocation()
  const [mode, setMode] = useState<Mode>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  if (!loading && session) {
    const target = (location.state as { from?: string } | null)?.from ?? '/'
    return <Navigate to={target} replace />
  }

  async function run(action: () => Promise<void>) {
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      await action()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    void run(async () => {
      if (mode === 'signin') {
        await auth.signInWithPassword(email.trim(), password)
      } else {
        const result = await auth.signUpWithPassword(email.trim(), password)
        if (result.needsEmailConfirmation) {
          setNotice(`We sent a confirmation link to ${email.trim()}. Open it, then sign in.`)
          setMode('signin')
          setPassword('')
        }
      }
    })
  }

  return (
    <div className="app">
      <div className="atmosphere" aria-hidden="true" />
      <section className="panel auth-card">
        <header className="panel-header">
          <h1 className="brand small">PlotPlanner</h1>
          <p>{mode === 'signin' ? 'Sign in to continue.' : 'Create your account.'}</p>
        </header>

        <form className="stack-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Email</span>
            <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              required
              minLength={6}
              autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <div className="actions">
            <button type="submit" className="btn primary" disabled={busy}>
              {mode === 'signin' ? 'Sign in' : 'Create account'}
            </button>
            {mode === 'signin' ? <button type="button" className="btn secondary" disabled={busy} onClick={() => run(auth.signInAsDemo)}>Continue as demo user</button> : null}
          </div>
        </form>

        <button
          type="button"
          className="link"
          onClick={() => {
            setMode(mode === 'signin' ? 'signup' : 'signin')
            setError(null)
            setNotice(null)
          }}
        >
          {mode === 'signin' ? 'New here? Create an account' : 'Already have an account? Sign in'}
        </button>
        {mode === 'signin' ? <Link className="link" to="/forgot-password">Forgot password?</Link> : null}

        {notice ? <p className="toast ok">{notice}</p> : null}
        {error ? (
          <p className="toast err" role="alert">
            {error}
          </p>
        ) : null}
      </section>
    </div>
  )
}
