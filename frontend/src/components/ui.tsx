import type { ReactNode } from 'react'
import { ApiError } from '../services/api'

export function errorText(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) return error.message
  return 'Something went wrong'
}

export function QueryState({
  pending,
  error,
  onRetry,
  empty,
  children,
}: {
  pending: boolean
  error: unknown
  onRetry?: () => void
  empty?: ReactNode
  children: ReactNode
}) {
  if (pending) return <p className="empty">Loading…</p>
  if (error) {
    return (
      <>
        <p className="toast err" role="alert">{errorText(error)}</p>
        {onRetry ? (
          <button type="button" className="btn secondary" onClick={onRetry}>Try again</button>
        ) : null}
      </>
    )
  }
  return <>{children ?? empty}</>
}

export function Notice({ error, ok }: { error?: unknown; ok?: string | null }) {
  if (error) return <p className="toast err" role="alert">{errorText(error)}</p>
  if (ok) return <p className="toast ok">{ok}</p>
  return null
}

/** Minimal markdown: paragraphs, lists, bold and links. Enough for chat replies. */
export function RichText({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/)
  return (
    <div className="rich">
      {blocks.map((block, index) => {
        const lines = block.split('\n')
        if (lines.every((line) => /^\s*[-*]\s+/.test(line))) {
          return (
            <ul key={index}>
              {lines.map((line, i) => <li key={i}>{inline(line.replace(/^\s*[-*]\s+/, ''))}</li>)}
            </ul>
          )
        }
        return <p key={index}>{inline(block)}</p>
      })}
    </div>
  )
}

function inline(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|\[[^\]]+\]\(https?:\/\/[^)]+\))/g)
  return parts.map((part, index) => {
    const link = part.match(/^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/)
    if (link) return <a key={index} href={link[2]} target="_blank" rel="noreferrer">{link[1]}</a>
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={index}>{part.slice(2, -2)}</strong>
    return <span key={index}>{part}</span>
  })
}

export function labelize(value: string): string {
  return value.replaceAll('_', ' ')
}
