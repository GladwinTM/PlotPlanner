import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useProfile } from '../hooks/useProfile'
import { errorText } from '../components/ui'
import { useAuth } from './AuthProvider'
import { LoadingState } from '../components/scrapbook'

/** Signed-in users who have not finished onboarding stay on that conversation. */
export function ProtectedRoute() {
  const { session, loading } = useAuth()
  const location = useLocation()
  const profile = useProfile()

  if (loading || (session && profile.isPending)) return <LoadingState fullPage label="Opening your workspace" />
  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (profile.isError) {
    return (
      <div className="app">
        <p className="toast err centered" role="alert">{errorText(profile.error)}</p>
        <p className="centered"><button type="button" className="btn secondary" onClick={() => void profile.refetch()}>Try again</button></p>
      </div>
    )
  }

  const done = profile.data?.onboarding_completed === true
  if (!done && location.pathname !== '/onboarding') return <Navigate to="/onboarding" replace />
  if (done && location.pathname === '/onboarding') return <Navigate to="/" replace />
  return <Outlet />
}
