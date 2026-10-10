import { useState, type FormEvent } from 'react'
import { createDocument } from '../api/client'
import type { DocumentRead, Profile, SourceType } from '../api/types'

type DocumentPanelProps = {
  profile: Profile | null
  onDocumentCreated: (document: DocumentRead) => void
}

const SOURCE_TYPES: { value: SourceType; label: string }[] = [
  { value: 'note', label: 'Note' },
  { value: 'resume', label: 'Resume' },
  { value: 'portfolio', label: 'Portfolio' },
  { value: 'job_description', label: 'Job description' },
]

export function DocumentPanel({ profile, onDocumentCreated }: DocumentPanelProps) {
  const [title, setTitle] = useState('')
  const [sourceType, setSourceType] = useState<SourceType>('note')
  const [sourceUri, setSourceUri] = useState('')
  const [content, setContent] = useState('')
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!profile) return

    setBusy(true)
    setError(null)
    setStatus(null)
    try {
      const document = await createDocument({
        profile_id: profile.id,
        title: title.trim(),
        source_type: sourceType,
        source_uri: sourceUri.trim() || null,
        content: content.trim(),
      })
      onDocumentCreated(document)
      setStatus(`Indexed “${document.title}” into ${document.chunk_count} chunks.`)
      setTitle('')
      setSourceUri('')
      setContent('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to ingest document')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Evidence</h2>
        <p>Ingest plain-text sources. The knowledge service chunks and embeds them.</p>
      </header>

      {!profile ? (
        <p className="empty">Create or load a profile before adding documents.</p>
      ) : (
        <form className="stack-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Title</span>
            <input
              required
              maxLength={300}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Spring internship reflections"
            />
          </label>

          <div className="row">
            <label className="field">
              <span>Source type</span>
              <select
                value={sourceType}
                onChange={(event) => setSourceType(event.target.value as SourceType)}
              >
                {SOURCE_TYPES.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field grow">
              <span>Source URI (optional)</span>
              <input
                maxLength={2000}
                value={sourceUri}
                onChange={(event) => setSourceUri(event.target.value)}
                placeholder="https://…"
              />
            </label>
          </div>

          <label className="field">
            <span>Content</span>
            <textarea
              required
              rows={8}
              maxLength={100000}
              value={content}
              onChange={(event) => setContent(event.target.value)}
              placeholder="Paste notes, resume text, portfolio writeups, or a job description."
            />
          </label>

          <div className="actions">
            <button type="submit" className="btn primary" disabled={busy || !title.trim() || !content.trim()}>
              {busy ? 'Indexing…' : 'Ingest document'}
            </button>
          </div>
        </form>
      )}

      {status ? <p className="toast ok">{status}</p> : null}
      {error ? <p className="toast err">{error}</p> : null}
    </section>
  )
}
