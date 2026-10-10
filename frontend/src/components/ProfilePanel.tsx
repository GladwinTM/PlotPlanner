import { useEffect, useState, type FormEvent } from 'react'
import { createProfile, getProfile, updateProfile } from '../api/client'
import type { Profile } from '../api/types'
import { TagInput } from './TagInput'

type ProfilePanelProps = {
  profile: Profile | null
  onProfileChange: (profile: Profile) => void
}

export function ProfilePanel({ profile, onProfileChange }: ProfilePanelProps) {
  const [displayName, setDisplayName] = useState('')
  const [bio, setBio] = useState('')
  const [interests, setInterests] = useState<string[]>([])
  const [goals, setGoals] = useState<string[]>([])
  const [lookupId, setLookupId] = useState('')
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!profile) return
    setDisplayName(profile.display_name)
    setBio(profile.bio ?? '')
    setInterests(profile.interests)
    setGoals(profile.goals)
    setLookupId(profile.id)
  }, [profile])

  function syncForm(next: Profile) {
    setDisplayName(next.display_name)
    setBio(next.bio ?? '')
    setInterests(next.interests)
    setGoals(next.goals)
    setLookupId(next.id)
    onProfileChange(next)
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    setStatus(null)
    try {
      const next = await createProfile({
        display_name: displayName.trim(),
        bio: bio.trim() || null,
        interests,
        goals,
      })
      syncForm(next)
      setStatus('Profile created. Save the ID to reopen it later.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create profile')
    } finally {
      setBusy(false)
    }
  }

  async function handleUpdate(event: FormEvent) {
    event.preventDefault()
    if (!profile) return
    setBusy(true)
    setError(null)
    setStatus(null)
    try {
      const next = await updateProfile(profile.id, {
        display_name: displayName.trim(),
        bio: bio.trim() || null,
        interests,
        goals,
      })
      syncForm(next)
      setStatus('Profile updated.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update profile')
    } finally {
      setBusy(false)
    }
  }

  async function handleLoad(event: FormEvent) {
    event.preventDefault()
    if (!lookupId.trim()) return
    setBusy(true)
    setError(null)
    setStatus(null)
    try {
      const next = await getProfile(lookupId.trim())
      syncForm(next)
      setStatus('Profile loaded.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load profile')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Profile</h2>
        <p>Store the interests and goals that ground every planning run.</p>
      </header>

      <form className="inline-form" onSubmit={handleLoad}>
        <label className="field grow">
          <span>Open existing profile</span>
          <input
            value={lookupId}
            onChange={(event) => setLookupId(event.target.value)}
            placeholder="Profile UUID"
          />
        </label>
        <button type="submit" className="btn secondary" disabled={busy}>
          Load
        </button>
      </form>

      <form className="stack-form" onSubmit={profile ? handleUpdate : handleCreate}>
        <label className="field">
          <span>Display name</span>
          <input
            required
            maxLength={120}
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            placeholder="Alex Rivera"
          />
        </label>

        <label className="field">
          <span>Bio</span>
          <textarea
            rows={4}
            maxLength={4000}
            value={bio}
            onChange={(event) => setBio(event.target.value)}
            placeholder="What you care about, where you are, what you are exploring."
          />
        </label>

        <TagInput
          label="Interests"
          values={interests}
          placeholder="systems design, climate tech, mentoring"
          onChange={setInterests}
        />

        <TagInput
          label="Goals"
          values={goals}
          placeholder="transition into product, ship a portfolio"
          onChange={setGoals}
        />

        <div className="actions">
          <button type="submit" className="btn primary" disabled={busy || !displayName.trim()}>
            {profile ? 'Save changes' : 'Create profile'}
          </button>
          {profile ? <code className="id-chip">{profile.id}</code> : null}
        </div>
      </form>

      {status ? <p className="toast ok">{status}</p> : null}
      {error ? <p className="toast err">{error}</p> : null}
    </section>
  )
}
