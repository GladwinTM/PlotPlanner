import { useState, type FormEvent, type ReactNode } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../app/AuthProvider'
import { sendPasswordReset, updatePassword } from '../services/auth'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null); setNotice(null)
    try {
      await sendPasswordReset(email.trim())
      // This wording intentionally does not reveal whether an address has an account.
      setNotice('If that email has a PlotPlanner account, we’ve sent a reset link. Check your inbox and spam folder.')
    } catch (err) { setError(err instanceof Error ? err.message : 'We could not send the reset email. Please try again.') } finally { setBusy(false) }
  }

  return <AuthCard title="Reset your password" description="We’ll email a secure link so you can choose a new password.">
    <form className="stack-form" onSubmit={submit}>
      <label className="field"><span>Email</span><input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
      <button className="btn primary" disabled={busy}>{busy ? 'Sending…' : 'Send reset link'}</button>
    </form>
    {notice ? <p className="toast ok" role="status">{notice}</p> : null}
    {error ? <p className="toast err" role="alert">{error}</p> : null}
    <Link className="link" to="/login">Back to sign in</Link>
  </AuthCard>
}

export function ResetPasswordPage() {
  const { session, loading } = useAuth()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  if (!loading && !session) return <Navigate to="/forgot-password" replace />

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(null)
    if (password !== confirm) { setError('The passwords do not match.'); return }
    setBusy(true)
    try { await updatePassword(password); setDone(true) } catch (err) { setError(err instanceof Error ? err.message : 'We could not update your password. Please request a new link.') } finally { setBusy(false) }
  }

  return <AuthCard title="Choose a new password" description="Use at least six characters. This link is for your account only.">
    {done ? <><p className="toast ok" role="status">Your password has been updated.</p><Link className="btn primary" to="/">Continue to PlotPlanner</Link></> : (
      <form className="stack-form" onSubmit={submit}>
        <label className="field"><span>New password</span><input type="password" minLength={6} autoComplete="new-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        <label className="field"><span>Confirm new password</span><input type="password" minLength={6} autoComplete="new-password" required value={confirm} onChange={(event) => setConfirm(event.target.value)} /></label>
        <button className="btn primary" disabled={busy || loading}>{busy ? 'Updating…' : 'Update password'}</button>
      </form>
    )}
    {error ? <p className="toast err" role="alert">{error}</p> : null}
  </AuthCard>
}

function AuthCard({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return <div className="app"><div className="atmosphere" aria-hidden="true" /><section className="panel auth-card"><header className="panel-header"><h1 className="brand small">PlotPlanner</h1><h2>{title}</h2><p>{description}</p></header>{children}</section></div>
}
