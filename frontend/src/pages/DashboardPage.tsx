import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { QueryState } from '../components/ui'
import { useProfile } from '../hooks/useProfile'
import { getOverview } from '../services/api'
import { Bulb, PaperCard, Shape, WashiLabel } from '../components/scrapbook'

export function DashboardPage() {
  const profile = useProfile()
  const overview = useQuery({ queryKey: ['overview'], queryFn: getOverview, retry: false })
  const name = profile.data?.display_name || 'there'

  return (
    <section className="page">
      <header className="page-head">
        <WashiLabel>Your plot</WashiLabel>
        <h1>Welcome back, {name}.</h1>
        <p>Pick up where you left off. Every number here comes from what you've actually done.</p>
      </header>
      <QueryState pending={overview.isPending} error={overview.error} onRetry={() => void overview.refetch()}>
        {overview.data ? (
          <>
            <div className="stat-row">
              <Stat label="Interests" value={overview.data.active_interests} tone="blue" />
              <Stat label="Active pathways" value={overview.data.active_courses} tone="yellow" />
              <Stat label="Goals in motion" value={overview.data.active_goals} tone="coral" />
              <Stat label="Minutes logged" value={overview.data.minutes_logged} tone="blue" />
            </div>
            <div className="split">
              <PaperCard tone="blue" taped className="panel">
                <header className="panel-header"><h2>Learning</h2></header>
                {overview.data.courses.length === 0 ? <EmptyLink to="/learn" text="No pathways yet. Generate one from an interest." /> : (
                  <ul className="plain">
                    {overview.data.courses.map((course) => (
                      <li key={course.course_id}>
                        <Link to={`/learn/${course.course_id}`}>{course.title}</Link>
                        <span>{course.percent}% · {course.enrollment}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </PaperCard>
              <PaperCard tone="coral" taped className="panel">
                <header className="panel-header"><h2>Goals</h2></header>
                {overview.data.goals.filter((g) => g.status === 'active').length === 0 ? <EmptyLink to="/goals" text="No active goals. Add one, career or personal." /> : (
                  <ul className="plain">
                    {overview.data.goals.filter((g) => g.status === 'active').map((goal) => (
                      <li key={goal.goal_id}><Link to="/goals">{goal.title}</Link><span>{goal.percent}%</span></li>
                    ))}
                  </ul>
                )}
              </PaperCard>
            </div>
            <PaperCard tone="yellow" className="panel feature-card">
              <Bulb /><header className="panel-header"><h2>Next</h2><p>Suggestions are rules over your activity, not guesses.</p></header>
              {overview.data.suggestions.length === 0 ? <p className="empty">Nothing to nudge. Keep going, or start something new in Explore.</p> : (
                <ul className="plain">{overview.data.suggestions.map((item) => <li key={item.message}>{item.message}</li>)}</ul>
              )}
            </PaperCard>
          </>
        ) : null}
      </QueryState>
    </section>
  )
}

function Stat({ label, value, tone }: { label: string; value: number; tone: 'blue' | 'coral' | 'yellow' }) {
  return <div className={`stat stat--${tone}`}><Shape shape={tone === 'yellow' ? 'star' : tone === 'coral' ? 'square' : 'circle'} tone={tone} size="sm" /><strong>{value}</strong><span>{label}</span></div>
}

function EmptyLink({ to, text }: { to: string; text: string }) {
  return <p className="empty"><Link to={to}>{text}</Link></p>
}
