import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../app/AuthProvider'
import { signOut } from '../services/auth'
import { Notice, QueryState, RichText } from '../components/ui'
import { useProfile } from '../hooks/useProfile'
import {
  completeOnboarding,
  onboardingTurn,
  retryOnboarding,
  saveOnboardingDraft,
  skipOnboarding,
  startOnboarding,
} from '../services/api'
import type { DraftGoal, DraftInterest, OnboardingDraft } from '../types/domain'
import { Bulb, Shape, WashiLabel } from '../components/scrapbook'

export function OnboardingPage() {
  const { session } = useAuth()
  const profile = useProfile()
  const name = profile.data?.display_name || session?.user.email?.split('@')[0] || 'there'
  const [intro, setIntro] = useState(true)
  const query = useQuery({ queryKey: ['onboarding'], queryFn: startOnboarding, retry: false })

  return (
    <div className="app onboard">
      <div className="atmosphere" aria-hidden="true" />
      <AnimatePresence mode="wait">
        {intro ? (
          <motion.section key="intro" className="intro" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="intro-shapes" aria-hidden="true"><Shape shape="star" tone="yellow" size="md" /><Shape shape="square" tone="coral" size="lg" /><Bulb /></div>
            <motion.div initial={{ y: 12, opacity: 0 }} animate={{ y: 0, opacity: 1 }}><WashiLabel tone="blue">PlotPlanner</WashiLabel></motion.div>
            <motion.h1 initial={{ y: 16, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.25 }}>
              Let’s make a little map of what makes you, you, {name}.
            </motion.h1>
            <motion.p className="lead" initial={{ y: 16, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.7 }}>
              One thought at a time. You’ll be able to review everything at the end.
            </motion.p>
            <motion.div className="actions" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.2 }}>
              <button type="button" className="btn primary" onClick={() => setIntro(false)}>Let's begin</button>
              <button type="button" className="btn secondary" onClick={() => void signOut()}>Sign out</button>
            </motion.div>
          </motion.section>
        ) : (
          <motion.section key="talk" className="talk" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <QueryState pending={query.isPending} error={query.error} onRetry={() => void query.refetch()}>
              {query.data ? <Conversation initial={query.data} /> : null}
            </QueryState>
          </motion.section>
        )}
      </AnimatePresence>
    </div>
  )
}

function Conversation({ initial }: { initial: Awaited<ReturnType<typeof startOnboarding>> }) {
  const client = useQueryClient()
  const navigate = useNavigate()
  const [draft, setDraft] = useState<OnboardingDraft>(initial.draft)
  const [text, setText] = useState('')
  const [status, setStatus] = useState(initial)
  const [note, setNote] = useState<string | null>(null)

  useEffect(() => { setDraft(status.draft) }, [status])

  const turn = useMutation({
    mutationFn: (message: string) => (status.awaiting_reply ? retryOnboarding() : onboardingTurn(message).then((r) => r.status)),
    onSuccess: (next) => { setStatus(next); setText(''); setNote(null) },
  })
  const save = useMutation({ mutationFn: () => saveOnboardingDraft(draft), onSuccess: (next) => { setStatus(next); setNote('Draft saved.') } })
  const finish = useMutation({
    mutationFn: () => completeOnboarding(draft),
    onSuccess: async (result) => {
      await client.invalidateQueries({ queryKey: ['profile'] })
      setNote(result.warnings[0] ?? `Your plot is ready: ${result.interests_created} interests, ${result.goals_created} goals.`)
      navigate('/')
    },
  })
  const skip = useMutation({
    mutationFn: skipOnboarding,
    onSuccess: async () => { await client.invalidateQueries({ queryKey: ['profile'] }); navigate('/') },
  })

  function send(event: FormEvent) {
    event.preventDefault()
    if (text.trim()) turn.mutate(text.trim())
  }

  return (
    <div className="talk-grid">
      <div className="panel thread">
        <header className="panel-header"><h2>Let's start with what you're doing right now.</h2></header>
        <ol className="messages">
          {status.messages.map((message) => (
            <li key={message.id} className={message.role}>
              {message.role === 'assistant' ? <RichText text={message.content} /> : <p>{message.content}</p>}
            </li>
          ))}
        </ol>
        {status.awaiting_reply ? <p className="toast err" role="alert">The last reply didn't come through. Your message is saved.</p> : null}
        <form className="composer" onSubmit={send}>
          <label className="field grow">
            <span className="sr">Your reply</span>
            <textarea rows={3} maxLength={4000} value={text} onChange={(e) => setText(e.target.value)} placeholder="A sentence or two is plenty. “I don't know” is a fine answer." />
          </label>
          <button type="submit" className="btn primary" disabled={turn.isPending || (!status.awaiting_reply && !text.trim())}>
            {turn.isPending ? 'Thinking…' : status.awaiting_reply ? 'Retry' : 'Send'}
          </button>
        </form>
        <Notice error={turn.error} />
      </div>
      {status.ready_to_finish ? (
        <aside className="panel review" aria-label="Review your answers">
          <header className="panel-header"><WashiLabel>Your review</WashiLabel><h2>Your plot so far</h2><p>Edit anything before you finish. Nothing here is saved to your profile until you do.</p></header>
          <DraftEditor draft={draft} onChange={setDraft} />
          <div className="actions">
            <button type="button" className="btn secondary" disabled={save.isPending} onClick={() => save.mutate()}>Save draft</button>
            <button type="button" className="btn primary" disabled={finish.isPending || (draft.interests.length === 0 && draft.goals.length === 0)} onClick={() => finish.mutate()}>{finish.isPending ? 'Building…' : 'Finish and build my plot'}</button>
            <button type="button" className="link" onClick={() => skip.mutate()}>Skip for now</button>
          </div>
          <Notice error={save.error ?? finish.error ?? skip.error} ok={note} />
        </aside>
      ) : (
        <aside className="panel onboarding-progress">
          <Bulb /><header className="panel-header"><WashiLabel tone="yellow">Your map</WashiLabel><h2>One question at a time</h2><p>Keep sharing what matters. Your editable review appears once the conversation is complete.</p></header>
          <div className="progress-string" aria-label="Onboarding in progress"><span /><span /><span /><span /></div>
          <button type="button" className="link" onClick={() => skip.mutate()} disabled={skip.isPending}>Skip for now</button>
          <Notice error={skip.error} />
        </aside>
      )}
    </div>
  )
}

function DraftEditor({ draft, onChange }: { draft: OnboardingDraft; onChange: (next: OnboardingDraft) => void }) {
  function setInterest(index: number, patch: Partial<DraftInterest>) {
    onChange({ ...draft, interests: draft.interests.map((item, i) => (i === index ? { ...item, ...patch } : item)) })
  }
  return (
    <div className="stack-form">
      <label className="field"><span>What you're doing now</span>
        <input value={draft.profile.current_occupation ?? ''} onChange={(e) => onChange({ ...draft, profile: { ...draft.profile, current_occupation: e.target.value || null } })} />
      </label>
      <label className="field"><span>Hours a week</span>
        <input type="number" min={0} max={168} value={draft.profile.available_hours_per_week ?? ''} onChange={(e) => onChange({ ...draft, profile: { ...draft.profile, available_hours_per_week: e.target.value === '' ? null : Number(e.target.value) } })} />
      </label>
      <fieldset className="draft-list">
        <legend>Interests</legend>
        {draft.interests.map((item, index) => (
          <div key={`${item.name}-${index}`} className="draft-row">
            <input aria-label={`Interest ${index + 1}`} value={item.name} onChange={(e) => setInterest(index, { name: e.target.value })} />
            <button type="button" className="link" onClick={() => onChange({ ...draft, interests: draft.interests.filter((_, i) => i !== index) })}>Remove</button>
          </div>
        ))}
        <button type="button" className="link" onClick={() => onChange({ ...draft, interests: [...draft.interests, { name: '', description: null, interest_type: 'personal', node_kind: 'secondary', category: null, priority: 3, seeks_income: false, parent: null }] })}>Add an interest</button>
      </fieldset>
      <fieldset className="draft-list">
        <legend>Goals</legend>
        {draft.goals.map((goal, index) => (
          <div key={`${goal.title}-${index}`} className="draft-row">
            <input aria-label={`Goal ${index + 1}`} value={goal.title} onChange={(e) => onChange({ ...draft, goals: draft.goals.map((g, i) => (i === index ? { ...g, title: e.target.value } : g)) })} />
            <button type="button" className="link" onClick={() => onChange({ ...draft, goals: draft.goals.filter((_, i) => i !== index) })}>Remove</button>
          </div>
        ))}
        <button type="button" className="link" onClick={() => onChange({ ...draft, goals: [...draft.goals, blankGoal()] })}>Add a goal</button>
      </fieldset>
      {draft.skills.length ? <p className="empty">Skills noted: {draft.skills.join(', ')}</p> : null}
    </div>
  )
}

function blankGoal(): DraftGoal {
  return { title: '', category: 'personal', target_outcome: null, priority: 3, hours_per_week: null }
}
