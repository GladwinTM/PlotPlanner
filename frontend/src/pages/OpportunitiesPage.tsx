import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Notice, QueryState, labelize } from '../components/ui'
import { createEarningPlan, deleteEarningPlan, listEarningPlans, listInterests, listOpportunities, salaryReport, saveOpportunity, searchJobs, setOpportunityStatus } from '../services/api'
import type { EarningPlan, Opportunity } from '../types/domain'

const TABS = ['Jobs', 'Tracked', 'Earning plans', 'Salary'] as const
const STATUSES = ['saved', 'applied', 'interviewing', 'offer', 'rejected', 'archived']

export function OpportunitiesPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>('Jobs')
  return (
    <section className="page">
      <header className="page-head">
        <p className="eyebrow">Things that can pay for you</p>
        <h1>Realistic ways to earn. No promises.</h1>
        <p>Jobs are live listings from public boards. Salaries appear only when the employer or provider published them. Plans are guidance.</p>
      </header>
      <div className="tabs" role="tablist">
        {TABS.map((item) => <button key={item} type="button" role="tab" aria-selected={tab === item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)}>{item}</button>)}
      </div>
      {tab === 'Jobs' ? <JobSearch /> : null}
      {tab === 'Tracked' ? <Tracked /> : null}
      {tab === 'Earning plans' ? <Plans /> : null}
      {tab === 'Salary' ? <Salary /> : null}
    </section>
  )
}

function JobSearch() {
  const [query, setQuery] = useState('')
  const [remote, setRemote] = useState(true)
  const search = useMutation({ mutationFn: () => searchJobs({ query, remote_only: remote, assess_fit: true }) })
  return (
    <div className="stack">
      <form className="inline-form" onSubmit={(e: FormEvent) => { e.preventDefault(); search.mutate() }}>
        <label className="field grow"><span>Role or skill</span><input required minLength={2} value={query} onChange={(e) => setQuery(e.target.value)} /></label>
        <label className="check"><input type="checkbox" checked={remote} onChange={(e) => setRemote(e.target.checked)} /> Remote only</label>
        <button className="btn primary" disabled={search.isPending}>{search.isPending ? 'Searching…' : 'Search'}</button>
      </form>
      <Notice error={search.error} />
      {search.data ? (
        <>
          <p className="empty">
            Sources: {search.data.attribution.map((a) => a.name).join(', ') || 'none'}.
            {search.data.fit_note ? ` ${search.data.fit_note}` : ''}
            {Object.keys(search.data.provider_errors).length ? ` Unavailable: ${Object.keys(search.data.provider_errors).join(', ')}.` : ''}
          </p>
          {search.data.results.length === 0 ? <p className="empty">No listings matched. Try a broader role.</p> : search.data.results.map((job) => <JobCard key={job.id} job={job} />)}
        </>
      ) : null}
    </div>
  )
}

function JobCard({ job }: { job: Opportunity }) {
  const client = useQueryClient()
  const save = useMutation({ mutationFn: () => saveOpportunity(job.id), onSuccess: () => client.invalidateQueries({ queryKey: ['opportunities'] }) })
  return (
    <article className="panel">
      <header className="panel-header">
        <h2>{job.title}</h2>
        <p>{job.company ?? 'Company not listed'} · {job.location ?? 'Location not listed'} · via {job.source}</p>
      </header>
      {job.fit_level ? <p><strong>AI fit: {labelize(job.fit_level)}.</strong> {job.fit_reason}</p> : null}
      {job.compensation_text ? <p>Pay listed ({labelize(job.compensation_basis ?? 'unknown')}): {job.compensation_text}</p> : <p className="empty">No salary published for this listing.</p>}
      {job.description ? <p>{job.description}</p> : null}
      <div className="actions">
        <a className="btn primary" href={job.canonical_url} target="_blank" rel="noreferrer">View original</a>
        {job.status === 'found' ? <button type="button" className="btn secondary" disabled={save.isPending} onClick={() => save.mutate()}>Save</button> : <span className="empty">Tracked as {labelize(job.status)}</span>}
      </div>
      <Notice error={save.error} />
    </article>
  )
}

function Tracked() {
  const client = useQueryClient()
  const list = useQuery({ queryKey: ['opportunities'], queryFn: () => listOpportunities(), retry: false })
  const update = useMutation({ mutationFn: (input: { id: string; status: string; notes?: string }) => setOpportunityStatus(input.id, input), onSuccess: () => client.invalidateQueries({ queryKey: ['opportunities'] }) })
  return (
    <QueryState pending={list.isPending} error={list.error} onRetry={() => void list.refetch()}>
      {(list.data ?? []).length === 0 ? <p className="empty">Nothing tracked yet. Save a listing from a search.</p> : (list.data ?? []).map((job) => (
        <article key={job.id} className="panel">
          <header className="panel-header"><h2>{job.title}</h2><p>{job.company} · {labelize(job.status)}</p></header>
          <div className="actions">
            <a href={job.canonical_url} target="_blank" rel="noreferrer">Original listing</a>
            <label className="field"><span>Status</span>
              <select value={job.status} onChange={(e) => update.mutate({ id: job.id, status: e.target.value })}>
                {STATUSES.map((status) => <option key={status} value={status}>{labelize(status)}</option>)}
              </select>
            </label>
          </div>
          <Notice error={update.error} />
        </article>
      ))}
    </QueryState>
  )
}

function Plans() {
  const client = useQueryClient()
  const plans = useQuery({ queryKey: ['plans'], queryFn: listEarningPlans, retry: false })
  const interests = useQuery({ queryKey: ['interests'], queryFn: listInterests })
  const [interest, setInterest] = useState('')
  const [focus, setFocus] = useState('')
  const create = useMutation({
    mutationFn: () => createEarningPlan({ interest_id: interest || undefined, focus: focus || undefined }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['plans'] }),
  })
  const remove = useMutation({ mutationFn: deleteEarningPlan, onSuccess: () => client.invalidateQueries({ queryKey: ['plans'] }) })
  return (
    <div className="stack">
      <form className="panel inline-form" onSubmit={(e: FormEvent) => { e.preventDefault(); create.mutate() }}>
        <label className="field"><span>Based on</span>
          <select value={interest} onChange={(e) => setInterest(e.target.value)}>
            <option value="">My whole profile</option>
            {(interests.data ?? []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
        <label className="field grow"><span>Focus</span><input value={focus} onChange={(e) => setFocus(e.target.value)} placeholder="Weekends only" /></label>
        <button className="btn primary" disabled={create.isPending}>{create.isPending ? 'Writing…' : 'Create plan'}</button>
        <Notice error={create.error} />
      </form>
      <QueryState pending={plans.isPending} error={plans.error} onRetry={() => void plans.refetch()}>
        {(plans.data ?? []).map((plan) => <PlanCard key={plan.id} plan={plan} onDelete={() => remove.mutate(plan.id)} />)}
      </QueryState>
    </div>
  )
}

const PLAN_LABELS: Record<string, string> = {
  readiness: 'Can you start now?', offer: 'What to offer', who_pays: 'Who might pay', portfolio: 'Portfolio',
  test_demand: 'Test demand', costs_and_pricing: 'Costs and pricing', evaluate_results: 'How to judge it', improve_next: 'What to improve',
}

function PlanCard({ plan, onDelete }: { plan: EarningPlan; onDelete: () => void }) {
  const body = plan.plan
  return (
    <article className="panel">
      <header className="panel-header"><h2>{plan.title}</h2><p>{labelize(plan.kind)} · AI guidance, not a promise of income</p></header>
      {Object.entries(PLAN_LABELS).map(([key, label]) => typeof body[key] === 'string' ? <p key={key}><strong>{label}. </strong>{String(body[key])}</p> : null)}
      {Array.isArray(body.what_you_need) ? <p><strong>You need: </strong>{(body.what_you_need as string[]).join('; ')}</p> : null}
      {Array.isArray(body.find_customers) ? <p><strong>Find people: </strong>{(body.find_customers as string[]).join('; ')}</p> : null}
      {Array.isArray(body.first_week) ? <ol>{(body.first_week as string[]).map((step) => <li key={step}>{step}</li>)}</ol> : null}
      {Array.isArray(body.cautions) ? <p className="empty">Watch for: {(body.cautions as string[]).join('; ')}</p> : null}
      <button type="button" className="link" onClick={onDelete}>Delete plan</button>
    </article>
  )
}

function Salary() {
  const [role, setRole] = useState('')
  const [remote, setRemote] = useState(false)
  const report = useMutation({ mutationFn: () => salaryReport({ role, remote_only: remote }) })
  return (
    <div className="stack">
      <form className="inline-form" onSubmit={(e: FormEvent) => { e.preventDefault(); report.mutate() }}>
        <label className="field grow"><span>Role</span><input required minLength={2} value={role} onChange={(e) => setRole(e.target.value)} /></label>
        <label className="check"><input type="checkbox" checked={remote} onChange={(e) => setRemote(e.target.checked)} /> Remote only</label>
        <button className="btn primary" disabled={report.isPending}>{report.isPending ? 'Checking…' : 'Check listed pay'}</button>
      </form>
      <Notice error={report.error} />
      {report.data ? (
        <article className="panel">
          <p>{report.data.note}</p>
          <p className="empty">{report.data.listings_checked} matching listings checked.</p>
          {report.data.groups.map((group) => (
            <p key={`${group.currency}-${group.period}-${group.basis}`}>
              <strong>{labelize(group.basis)}</strong> · {group.sample_size} listings · {group.currency} per {group.period}: low {Math.round(group.low).toLocaleString()}, median {Math.round(group.median).toLocaleString()}, high {Math.round(group.high).toLocaleString()}.
            </p>
          ))}
          <ul className="plain">
            {report.data.evidence.map((item) => (
              <li key={item.url}><a href={item.url} target="_blank" rel="noreferrer">{item.title}</a><span>{item.compensation_text} · {labelize(item.basis)} · {item.source}</span></li>
            ))}
          </ul>
        </article>
      ) : null}
    </div>
  )
}
