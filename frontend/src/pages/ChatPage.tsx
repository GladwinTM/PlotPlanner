import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Notice, QueryState, RichText, labelize } from '../components/ui'
import { decideProposal, deleteConversation, getConversation, listConversations, retryChat, sendChat } from '../services/api'
import type { Conversation } from '../types/domain'

export function ChatPage() {
  const client = useQueryClient()
  const conversations = useQuery({ queryKey: ['conversations'], queryFn: listConversations, retry: false })
  const [active, setActive] = useState<string | null>(null)
  const thread = useQuery({ queryKey: ['conversation', active], queryFn: () => getConversation(active!), enabled: Boolean(active), retry: false })
  const [text, setText] = useState('')
  const send = useMutation({
    mutationFn: () => sendChat(text, active ?? undefined),
    onSuccess: (next) => { setActive(next.id); setText(''); client.setQueryData(['conversation', next.id], next); void client.invalidateQueries({ queryKey: ['conversations'] }) },
  })
  const retry = useMutation({
    mutationFn: () => retryChat(active!),
    onSuccess: (next) => client.setQueryData(['conversation', next.id], next),
  })
  const remove = useMutation({
    mutationFn: deleteConversation,
    onSuccess: () => { setActive(null); void client.invalidateQueries({ queryKey: ['conversations'] }) },
  })
  const current = thread.data
  const waiting = current?.messages.at(-1)?.role === 'user'

  return (
    <section className="page chat-page">
      <aside className="panel chat-list">
        <header className="panel-header"><h2>Chats</h2></header>
        <button type="button" className="btn secondary" onClick={() => setActive(null)}>New chat</button>
        <QueryState pending={conversations.isPending} error={conversations.error} onRetry={() => void conversations.refetch()}>
          <ul className="plain">
            {(conversations.data ?? []).map((item) => (
              <li key={item.id}><button type="button" className="link" onClick={() => setActive(item.id)}>{item.title || 'Untitled'}</button></li>
            ))}
          </ul>
        </QueryState>
      </aside>
      <div className="panel thread">
        {active && thread.isPending ? <p className="empty">Loading…</p> : null}
        {thread.isError ? <Notice error={thread.error} /> : null}
        <ol className="messages">
          {(current?.messages ?? []).map((message) => (
            <li key={message.id} className={message.role}>
              {message.role === 'assistant' ? <RichText text={message.content} /> : <p>{message.content}</p>}
              {message.meta.sources?.length ? (
                <ul className="sources">{message.meta.sources.map((source) => (
                  <li key={source.url}><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a> · {source.provider}{source.salary ? ` · ${source.salary}` : ''}</li>
                ))}</ul>
              ) : null}
              {message.meta.proposals?.map((proposal, index) => (
                <ProposalRow key={`${message.id}-${index}`} messageId={message.id} index={index} proposal={proposal} onDone={(next) => {
                  if (!current) return
                  client.setQueryData(['conversation', current.id], { ...current, messages: current.messages.map((m) => m.id === next.id ? next : m) } satisfies Conversation)
                }} />
              ))}
            </li>
          ))}
        </ol>
        {waiting ? <p className="toast err" role="alert">No reply yet. Your message is saved.</p> : null}
        <form className="composer" onSubmit={(e: FormEvent) => { e.preventDefault(); if (text.trim() && !waiting) send.mutate() }}>
          <label className="field grow"><span className="sr">Message</span>
            <textarea rows={3} maxLength={4000} value={text} onChange={(e) => setText(e.target.value)} placeholder="What should I work on this week?" />
          </label>
          <div className="actions">
            <button className="btn primary" disabled={send.isPending || waiting || !text.trim()}>{send.isPending ? 'Thinking…' : 'Send'}</button>
            {waiting ? <button type="button" className="btn secondary" disabled={retry.isPending} onClick={() => retry.mutate()}>Retry</button> : null}
            {active ? <button type="button" className="link" onClick={() => remove.mutate(active)}>Delete chat</button> : null}
          </div>
        </form>
        <Notice error={send.error ?? retry.error ?? remove.error} />
      </div>
    </section>
  )
}

function ProposalRow({ messageId, index, proposal, onDone }: { messageId: string; index: number; proposal: NonNullable<Conversation['messages'][number]['meta']['proposals']>[number]; onDone: (message: Conversation['messages'][number]) => void }) {
  const decide = useMutation({ mutationFn: (accept: boolean) => decideProposal(messageId, index, accept), onSuccess: onDone })
  const what = proposal.change_type === 'update_weekly_hours' ? `Set weekly hours to ${proposal.hours}` : `${labelize(proposal.change_type)}: ${proposal.name}`
  return (
    <div className="proposal">
      <p><strong>{what}.</strong> {proposal.reason}</p>
      {proposal.status === 'pending' ? (
        <div className="actions">
          <button type="button" className="btn primary" disabled={decide.isPending} onClick={() => decide.mutate(true)}>Accept</button>
          <button type="button" className="btn secondary" disabled={decide.isPending} onClick={() => decide.mutate(false)}>Dismiss</button>
        </div>
      ) : <p className="empty">{proposal.status === 'accepted' ? proposal.result : 'Dismissed'}</p>}
      <Notice error={decide.error} />
    </div>
  )
}
