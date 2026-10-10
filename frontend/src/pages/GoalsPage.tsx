import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Notice, QueryState, labelize } from '../components/ui'
import { addCheckin, addMilestone, createGoal, deleteGoal, listGoals, listInterests, planGoal, updateGoal, updateMilestone } from '../services/api'
import type { Goal } from '../types/domain'

const CATEGORIES = ['career', 'learning', 'health', 'creative', 'personal', 'financial', 'community', 'other']

export function GoalsPage() {
  const client = useQueryClient()
  const goals = useQuery({ queryKey: ['goals'], queryFn: listGoals, retry: false })
  const refresh = () => client.invalidateQueries({ queryKey: ['goals'] })
  return (
    <section className="page">
      <header className="page-head">
        <p className="eyebrow">Goals</p>
        <h1>Career, creative, personal. All of them count.</h1>
        <p>Progress is completed milestones. Plans are a starting point you can edit.</p>
      </header>
      <NewGoal onDone={refresh} />
      <QueryState pending={goals.isPending} error={goals.error} onRetry={() => void goals.refetch()}>
        <div className="stack">{(goals.data ?? []).map((goal) => <GoalCard key={goal.id} goal={goal} onDone={refresh} />)}</div>
        {goals.data?.length === 0 ? <p className="empty">No goals yet.</p> : null}
      </QueryState>
    </section>
  )
}

function NewGoal({ onDone }: { onDone: () => Promise<void> }) {
  const interests = useQuery({ queryKey: ['interests'], queryFn: listInterests })
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('personal')
  const [interest, setInterest] = useState('')
  const create = useMutation({
    mutationFn: () => createGoal({ title, category, interest_id: interest || null }),
    onSuccess: async () => { setTitle(''); await onDone() },
  })
  return (
    <form className="panel inline-form" onSubmit={(e: FormEvent) => { e.preventDefault(); create.mutate() }}>
      <label className="field grow"><span>Goal</span><input required maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} /></label>
      <label className="field"><span>Category</span>
        <select value={category} onChange={(e) => setCategory(e.target.value)}>{CATEGORIES.map((c) => <option key={c} value={c}>{labelize(c)}</option>)}</select>
      </label>
      <label className="field"><span>Interest</span>
        <select value={interest} onChange={(e) => setInterest(e.target.value)}>
          <option value="">None</option>
          {(interests.data ?? []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
      </label>
      <button className="btn primary" disabled={create.isPending}>Add</button>
      <Notice error={create.error} />
    </form>
  )
}

function GoalCard({ goal, onDone }: { goal: Goal; onDone: () => Promise<void> }) {
  const [adjustment, setAdjustment] = useState('')
  const [milestone, setMilestone] = useState('')
  const [minutes, setMinutes] = useState('')
  const [note, setNote] = useState('')
  const run = useMutation({ mutationFn: (fn: () => Promise<unknown>) => fn(), onSuccess: onDone })
  return (
    <article className="panel">
      <header className="panel-header">
        <h2>{goal.title}</h2>
        <p>{labelize(goal.category)} · {labelize(goal.status)} · {goal.progress_percent}% · {goal.minutes_logged} min logged</p>
      </header>
      {goal.plan_summary ? <p>{goal.plan_summary}</p> : null}
      {goal.target_outcome ? <p className="empty">Outcome: {goal.target_outcome}</p> : null}
      <ol className="milestones">
        {goal.milestones.map((item) => (
          <li key={item.id}>
            <label className="check">
              <input type="checkbox" checked={Boolean(item.completed_at)} onChange={(e) => run.mutate(() => updateMilestone(goal.id, item.id, { completed: e.target.checked }))} />
              <span>{item.title}{item.due_date ? ` · by ${item.due_date}` : ''} · {item.source}</span>
            </label>
            {item.description ? <p className="empty">{item.description}</p> : null}
          </li>
        ))}
      </ol>
      <form className="inline-form" onSubmit={(e) => { e.preventDefault(); run.mutate(() => planGoal(goal.id, adjustment || undefined)) }}>
        <label className="field grow"><span>Adjust the plan</span><input value={adjustment} onChange={(e) => setAdjustment(e.target.value)} placeholder="I only have 2 hours a week" /></label>
        <button className="btn secondary" disabled={run.isPending}>{goal.milestones.some((m) => m.source === 'ai') ? 'Regenerate plan' : 'Generate plan'}</button>
      </form>
      <form className="inline-form" onSubmit={(e) => { e.preventDefault(); run.mutate(() => addMilestone(goal.id, milestone)); setMilestone('') }}>
        <label className="field grow"><span>Your own milestone</span><input value={milestone} onChange={(e) => setMilestone(e.target.value)} /></label>
        <button className="btn secondary" disabled={!milestone.trim()}>Add</button>
      </form>
      <form className="inline-form" onSubmit={(e) => { e.preventDefault(); run.mutate(() => addCheckin(goal.id, { note: note || undefined, minutes: minutes ? Number(minutes) : undefined })); setNote(''); setMinutes('') }}>
        <label className="field grow"><span>Check in</span><input value={note} onChange={(e) => setNote(e.target.value)} placeholder="What you did" /></label>
        <label className="field narrow"><span>Minutes</span><input type="number" min={0} max={1440} value={minutes} onChange={(e) => setMinutes(e.target.value)} /></label>
        <button className="btn secondary" disabled={!note.trim() && minutes === ''}>Log</button>
      </form>
      <div className="actions">
        {goal.status !== 'completed' ? <button type="button" className="btn secondary" onClick={() => run.mutate(() => updateGoal(goal.id, { status: 'completed' }))}>Mark complete</button> : <button type="button" className="btn secondary" onClick={() => run.mutate(() => updateGoal(goal.id, { status: 'active' }))}>Reopen</button>}
        <button type="button" className="btn secondary" onClick={() => run.mutate(() => updateGoal(goal.id, { status: goal.status === 'paused' ? 'active' : 'paused' }))}>{goal.status === 'paused' ? 'Resume' : 'Pause'}</button>
        <button type="button" className="link" onClick={() => run.mutate(() => deleteGoal(goal.id))}>Delete</button>
      </div>
      <Notice error={run.error} />
    </article>
  )
}
