import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { QueryState } from '../components/ui'
import { getActivity, getInterestAnalytics, getOverview } from '../services/api'

export function AnalyticsPage() {
  const overview = useQuery({ queryKey: ['overview'], queryFn: getOverview, retry: false })
  const interests = useQuery({ queryKey: ['interest-analytics'], queryFn: getInterestAnalytics, retry: false })
  const activity = useQuery({ queryKey: ['activity'], queryFn: () => getActivity(84), retry: false })
  const recent = (activity.data?.series ?? []).filter((_, index, all) => index >= all.length - 28)

  return (
    <section className="page">
      <header className="page-head">
        <p className="eyebrow">Insights</p>
        <h1>What you've actually done.</h1>
        <p>{overview.data?.definitions.course_percent} {overview.data?.definitions.minutes_logged}</p>
      </header>
      <QueryState pending={overview.isPending || activity.isPending} error={overview.error ?? activity.error} onRetry={() => { void overview.refetch(); void activity.refetch() }}>
        <div className="stat-row">
          <div className="stat"><strong>{overview.data?.completed_activities ?? 0}</strong><span>Activities done</span></div>
          <div className="stat"><strong>{overview.data?.completed_modules ?? 0}</strong><span>Modules done</span></div>
          <div className="stat"><strong>{overview.data?.completed_projects ?? 0}</strong><span>Projects finished</span></div>
          <div className="stat"><strong>{overview.data?.tracked_opportunities ?? 0}</strong><span>Tracked jobs</span></div>
        </div>
        <article className="panel chart">
          <header className="panel-header"><h2>Last 4 weeks</h2><p>Completions, check-ins and minutes you logged.</p></header>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={recent}>
                <XAxis dataKey="date" tickFormatter={(value: string) => value.slice(5)} minTickGap={24} />
                <YAxis allowDecimals={false} width={32} />
                <Tooltip />
                <Bar dataKey="activities_completed" name="Activities" fill="#0f6e56" />
                <Bar dataKey="checkins" name="Check-ins" fill="#c4913a" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>
      </QueryState>
      <QueryState pending={interests.isPending} error={interests.error} onRetry={() => void interests.refetch()}>
        {interests.data ? (
          <article className="panel">
            <header className="panel-header"><h2>Interests</h2><p>{interests.data.note}</p></header>
            <ul className="plain">
              {interests.data.interests.map((item) => (
                <li key={item.id}>
                  <span>{item.name}</span>
                  <span>{item.connections} links · {item.enrolled_courses} pathways{item.average_course_percent !== null ? ` · ${item.average_course_percent}%` : ''} · {item.goals} goals</span>
                </li>
              ))}
            </ul>
          </article>
        ) : null}
      </QueryState>
    </section>
  )
}
