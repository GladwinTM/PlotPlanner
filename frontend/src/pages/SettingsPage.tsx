import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Notice } from '../components/ui'
import { useProfile, useUpdateProfile } from '../hooks/useProfile'
import { deleteAccountData, deleteFact, listFacts, updateFact } from '../services/api'
import type { Profile } from '../types/profile'
import { LoadingState } from '../components/scrapbook'

type FormValues = {
  display_name: string
  location: string
  current_occupation: string
  education_summary: string
  experience_summary: string
  available_hours_per_week: string
  learning_preferences: string
  constraints_summary: string
}

function toForm(profile: Profile): FormValues {
  return {
    display_name: profile.display_name,
    location: profile.location ?? '',
    current_occupation: profile.current_occupation ?? '',
    education_summary: profile.education_summary ?? '',
    experience_summary: profile.experience_summary ?? '',
    available_hours_per_week: profile.available_hours_per_week?.toString() ?? '',
    learning_preferences: profile.learning_preferences ?? '',
    constraints_summary: profile.constraints_summary ?? '',
  }
}

function ProfileForm({ profile }: { profile: Profile }) {
  const update = useUpdateProfile()
  const [values, setValues] = useState<FormValues>(() => toForm(profile))
  const [saved, setSaved] = useState(false)

  function set<K extends keyof FormValues>(name: K, value: FormValues[K]) {
    setSaved(false)
    setValues((current) => ({ ...current, [name]: value }))
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaved(false)
    // Blank optional fields are sent as "" and cleared by the server.
    const hours = values.available_hours_per_week.trim()
    update.mutate({
      ...values,
      available_hours_per_week: hours === '' ? null : Number(hours),
    }, {
      onSuccess: (next) => {
        setValues(toForm(next))
        setSaved(true)
      },
    })
  }

  return (
    <form className="stack-form" onSubmit={handleSubmit}>
      <label className="field">
        <span>Display name</span>
        <input required maxLength={120} value={values.display_name} onChange={(e) => set('display_name', e.target.value)} />
      </label>
      <label className="field">
        <span>Location</span>
        <input maxLength={200} value={values.location} onChange={(e) => set('location', e.target.value)} />
      </label>
      <label className="field">
        <span>Current occupation</span>
        <input
          maxLength={200}
          value={values.current_occupation}
          onChange={(e) => set('current_occupation', e.target.value)}
        />
      </label>
      <label className="field">
        <span>Education</span>
        <textarea
          rows={3}
          maxLength={4000}
          value={values.education_summary}
          onChange={(e) => set('education_summary', e.target.value)}
        />
      </label>
      <label className="field">
        <span>Experience</span>
        <textarea
          rows={4}
          maxLength={4000}
          value={values.experience_summary}
          onChange={(e) => set('experience_summary', e.target.value)}
        />
      </label>
      <label className="field">
        <span>Hours available each week</span>
        <input type="number" min={0} max={168} value={values.available_hours_per_week} onChange={(e) => set('available_hours_per_week', e.target.value)} />
      </label>
      <label className="field">
        <span>How you like to learn</span>
        <input maxLength={1000} value={values.learning_preferences} onChange={(e) => set('learning_preferences', e.target.value)} />
      </label>
      <label className="field">
        <span>Constraints</span>
        <textarea rows={2} maxLength={2000} value={values.constraints_summary} onChange={(e) => set('constraints_summary', e.target.value)} />
      </label>
      <div className="actions">
        <button type="submit" className="btn primary" disabled={update.isPending || !values.display_name.trim()}>
          {update.isPending ? 'Saving…' : 'Save changes'}
        </button>
      </div>
      {saved ? <p className="toast ok">Profile saved.</p> : null}
      {update.isError ? (
        <p className="toast err" role="alert">
          {update.error.message}
        </p>
      ) : null}
    </form>
  )
}

export function SettingsPage() {
  const { data: profile, isPending, isError, error, refetch } = useProfile()

  return (
    <section className="panel settings">
      <header className="panel-header">
        <h2>Your profile</h2>
        <p>The basics PlotPlanner uses to personalise your plans. You can change them any time.</p>
      </header>

      {isPending ? <LoadingState label="Gathering your profile" /> : null}
      {isError ? (
        <>
          <p className="toast err" role="alert">
            {error.message}
          </p>
          <div className="actions">
            <button type="button" className="btn secondary" onClick={() => void refetch()}>
              Try again
            </button>
          </div>
        </>
      ) : null}
      {profile ? <ProfileForm key={profile.updated_at} profile={profile} /> : null}
      <Facts />
      <DeleteData />
    </section>
  )
}

function Facts() {
  const facts = useQuery({ queryKey: ['facts'], queryFn: () => listFacts(), retry: false })
  const client = useQueryClient()
  const refresh = () => client.invalidateQueries({ queryKey: ['facts'] })
  const update = useMutation({ mutationFn: (input: { id: string; confirmed: boolean }) => updateFact(input.id, { confirmed: input.confirmed }), onSuccess: refresh })
  const remove = useMutation({ mutationFn: deleteFact, onSuccess: refresh })
  if (facts.isPending || facts.isError || !facts.data?.length) return null
  return (
    <div className="stack-form">
      <h3>Facts on your profile</h3>
      {facts.data.map((fact) => (
        <div key={fact.id} className="draft-row">
          <span>{fact.kind}: {fact.value} · {fact.source}{fact.confirmed ? '' : ' · unconfirmed'}</span>
          <button type="button" className="btn secondary" onClick={() => update.mutate({ id: fact.id, confirmed: !fact.confirmed })}>{fact.confirmed ? 'Unconfirm' : 'Confirm'}</button>
          <button type="button" className="link" onClick={() => remove.mutate(fact.id)}>Remove</button>
        </div>
      ))}
    </div>
  )
}

function DeleteData() {
  const [armed, setArmed] = useState(false)
  const wipe = useMutation({ mutationFn: deleteAccountData })
  return (
    <div className="stack-form">
      <h3>Delete PlotPlanner data</h3>
      <p className="empty">Removes your profile, interests, courses, goals, chats and documents. Your sign-in account stays, because deleting it needs a key this server does not hold.</p>
      {armed ? <button type="button" className="btn secondary" onClick={() => wipe.mutate()}>{wipe.isPending ? 'Deleting…' : 'Confirm delete'}</button> : <button type="button" className="btn secondary" onClick={() => setArmed(true)}>Delete my data</button>}
      <Notice error={wipe.error} ok={wipe.data?.note} />
    </div>
  )
}
