import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Notice, QueryState, labelize } from '../components/ui'
import { deleteDocument, deleteFact, getDocument, listDocuments, updateFact, uploadDocument } from '../services/api'

export function DocumentsPage() {
  const client = useQueryClient()
  const documents = useQuery({ queryKey: ['documents'], queryFn: listDocuments, retry: false })
  const [open, setOpen] = useState<string | null>(null)
  const detail = useQuery({ queryKey: ['document', open], queryFn: () => getDocument(open!), enabled: Boolean(open), retry: false })
  const upload = useMutation({
    mutationFn: (file: File) => uploadDocument(file),
    onSuccess: (doc) => { setOpen(doc.id); void client.invalidateQueries({ queryKey: ['documents'] }) },
  })
  const remove = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => { setOpen(null); void client.invalidateQueries({ queryKey: ['documents'] }) },
  })

  return (
    <section className="page">
      <header className="page-head">
        <p className="eyebrow">Documents</p>
        <h1>Bring a resume. Check what we read.</h1>
        <p>PDF, DOCX or TXT, up to 10 MB. Extracted facts stay suggestions until you confirm them. Files stay private.</p>
      </header>
      <label className="btn secondary upload">
        {upload.isPending ? 'Reading…' : 'Upload a document'}
        <input type="file" accept=".pdf,.docx,.txt,application/pdf,text/plain" hidden onChange={(e) => { const file = e.target.files?.[0]; if (file) upload.mutate(file); e.target.value = '' }} />
      </label>
      <Notice error={upload.error} />
      <QueryState pending={documents.isPending} error={documents.error} onRetry={() => void documents.refetch()}>
        <ul className="plain">
          {(documents.data ?? []).map((doc) => (
            <li key={doc.id}>
              <button type="button" className="link" onClick={() => setOpen(doc.id)}>{doc.filename}</button>
              <span>{labelize(doc.processing_status)} · {Math.ceil(doc.size_bytes / 1024)} KB</span>
            </li>
          ))}
        </ul>
        {documents.data?.length === 0 ? <p className="empty">No documents yet.</p> : null}
      </QueryState>
      {open && detail.data ? (
        <article className="panel">
          <header className="panel-header">
            <h2>{detail.data.filename}</h2>
            <p>{labelize(detail.data.processing_status)}{detail.data.error ? ` — ${detail.data.error}` : ''}</p>
          </header>
          {detail.data.text_preview ? <pre className="preview">{detail.data.text_preview}</pre> : null}
          <h3>Facts to review</h3>
          {detail.data.facts.length === 0 ? <p className="empty">Nothing was extracted.</p> : detail.data.facts.map((fact) => <FactRow key={fact.id} fact={fact} onChange={() => void detail.refetch()} />)}
          <button type="button" className="link" onClick={() => remove.mutate(open)}>Delete document and unconfirmed facts</button>
          <Notice error={remove.error} />
        </article>
      ) : null}
      {detail.isError ? <Notice error={detail.error} /> : null}
    </section>
  )
}

function FactRow({ fact, onChange }: { fact: { id: string; kind: string; value: string; confirmed: boolean }; onChange: () => void }) {
  const update = useMutation({ mutationFn: (confirmed: boolean) => updateFact(fact.id, { confirmed }), onSuccess: onChange })
  const remove = useMutation({ mutationFn: () => deleteFact(fact.id), onSuccess: onChange })
  return (
    <div className="draft-row">
      <span><strong>{labelize(fact.kind)}:</strong> {fact.value} {fact.confirmed ? '(confirmed)' : '(unconfirmed)'}</span>
      {!fact.confirmed ? <button type="button" className="btn secondary" onClick={() => update.mutate(true)}>Confirm</button> : <button type="button" className="btn secondary" onClick={() => update.mutate(false)}>Unconfirm</button>}
      <button type="button" className="link" onClick={() => remove.mutate()}>Remove</button>
    </div>
  )
}
