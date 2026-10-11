import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  Compass,
  Goal,
  House,
  LineChart,
  LogOut,
  MessageCircle,
  Route,
  Settings,
  Sparkles,
  Wallet,
} from 'lucide-react'
import { useAuth } from '../../app/AuthProvider'
import { Bulb, Shape } from '../scrapbook'

const LINKS = [
  { to: '/', label: 'Home', icon: House, end: true },
  { to: '/explore', label: 'Explore', icon: Compass },
  { to: '/learn', label: 'Learn', icon: Route },
  { to: '/goals', label: 'Goals', icon: Goal },
  { to: '/earn', label: 'Earn', icon: Wallet },
  { to: '/chat', label: 'Chat', icon: MessageCircle },
  { to: '/documents', label: 'Documents', icon: Sparkles },
  { to: '/insights', label: 'Insights', icon: LineChart },
  { to: '/settings', label: 'Profile', icon: Settings },
]

export function AppLayout() {
  const { session, signOut } = useAuth()
  const [error, setError] = useState<string | null>(null)

  async function handleSignOut() {
    setError(null)
    try {
      await signOut()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign out failed')
    }
  }

  return (
    <div className="shell">
      <div className="atmosphere" aria-hidden="true" />
      <aside className="sidebar">
        <div className="brand-lockup"><span className="brand-mark" aria-hidden="true"><Shape shape="circle" tone="blue" size="sm" /><Shape shape="square" tone="coral" size="sm" /><span className="brand-thread" /></span><p className="brand small">PlotPlanner</p></div>
        <nav className="side-nav" aria-label="Main">
          {LINKS.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end}>
              <Icon size={18} aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="side-user">
          <Bulb />
          <strong>{session?.user.email ?? 'Account'}</strong>
          <button type="button" className="btn secondary" onClick={handleSignOut}>
            <LogOut size={16} aria-hidden="true" /> Sign out
          </button>
        </div>
      </aside>
      <div className="shell-main">
        {error ? <p className="toast err" role="alert">{error}</p> : null}
        <main>
          <Outlet />
        </main>
      </div>
      <nav className="tabbar" aria-label="Main mobile">
        {LINKS.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end}>
            <Icon size={18} aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
