import { useState, type FormEvent } from 'react'
import { searchEvidence } from '../api/client'
import type { Profile, SearchResult } from '../api/types'

type SearchPanelProps = {
  profile: Profile | null
}

export function SearchPanel({ profile }: SearchPanelProps) {
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(5)
  const [results, setResults] = useState<SearchResult[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [searched, setSearched] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!profile || query.trim().length < 2) return

    setBusy(true)
    setError(null)
    try {
      const next = await searchEvidence({
        profile_id: profile.id,
        query: query.trim(),
        limit,
      })
      setResults(next)
      setSearched(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
      setResults([])
      setSearched(true)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Retrieve</h2>
        <p>Semantically search this profile’s indexed evidence before planning.</p>
      </header>

      {!profile ? (
        <p className="empty">Create or load a profile to search its knowledge base.</p>
      ) : (
        <>
          <form className="inline-form" onSubmit={handleSubmit}>
            <label className="field grow">
              <span>Query</span>
              <input
                required
                minLength={2}
                maxLength={2000}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="leadership under ambiguity"
              />
            </label>
            <label className="field narrow">
              <span>Limit</span>
              <input
                type="number"
                min={1}
                max={20}
                value={limit}
                onChange={(event) => setLimit(Number(event.target.value))}
              />
            </label>
            <button type="submit" className="btn primary" disabled={busy || query.trim().length < 2}>
              {busy ? 'Searching…' : 'Search'}
            </button>
          </form>

          {error ? <p className="toast err">{error}</p> : null}

          {searched && !error ? (
            results.length === 0 ? (
              <p className="empty">No matching chunks yet. Ingest a document first.</p>
            ) : (
              <ul className="results">
                {results.map((result, index) => (
                  <li key={`${result.document_id}-${index}`}>
                    <div className="result-meta">
                      <strong>{result.document_title}</strong>
                      <span>{(result.score * 100).toFixed(1)}% match</span>
                    </div>
                    <p>{result.content}</p>
                  </li>
                ))}
              </ul>
            )
          ) : null}
        </>
      )}
    </section>
  )
}
