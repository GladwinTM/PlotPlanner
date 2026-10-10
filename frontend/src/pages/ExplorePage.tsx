import { Background, Controls, ReactFlow, type Edge, type Node, type NodeProps } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useMemo, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Notice, QueryState, labelize } from '../components/ui'
import { createInterest, createRelationship, deleteInterest, deleteRelationship, getGraph, saveLayout, suggestInterests, updateInterest } from '../services/api'
import type { GraphNode } from '../types/domain'

const nodeTypes = { interest: InterestNode }

export function ExplorePage() {
  const client = useQueryClient()
  const graph = useQuery({ queryKey: ['graph'], queryFn: getGraph, retry: false })
  const [selected, setSelected] = useState<string | null>(null)
  const [moved, setMoved] = useState<Record<string, { x: number; y: number }>>({})
  const [notice, setNotice] = useState<string | null>(null)
  const refresh = () => client.invalidateQueries({ queryKey: ['graph'] })

  const nodes = useMemo(() => layout(graph.data?.nodes ?? [], moved), [graph.data, moved])
  const edges: Edge[] = (graph.data?.edges ?? []).map((edge) => ({
    id: edge.id, source: edge.source, target: edge.target, label: labelize(edge.relationship_type),
  }))
  const current = graph.data?.nodes.find((node) => node.id === selected) ?? null

  const persist = useMutation({
    mutationFn: () => saveLayout(nodes.map((node) => ({ id: node.id, x: node.position.x, y: node.position.y }))),
    onSuccess: async (result) => { setMoved({}); setNotice(`Layout saved for ${result.updated} interests.`); await refresh() },
  })
  const suggestions = useMutation({ mutationFn: suggestInterests })

  return (
    <section className="page">
      <header className="page-head">
        <p className="eyebrow">Interest network</p>
        <h1>Everything you're exploring.</h1>
        <p>Main areas, skills and the links between them. Progress shows completed course work, not a career score.</p>
      </header>
      <QueryState pending={graph.isPending} error={graph.error} onRetry={() => void graph.refetch()}>
        <div className="graph-wrap">
          {nodes.length === 0 ? <p className="empty canvas-empty">No interests yet. Add the first one below.</p> : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              fitView
              onNodeClick={(_, node) => setSelected(node.id)}
              onNodeDragStop={(_, node) => setMoved((current) => ({ ...current, [node.id]: node.position }))}
            >
              <Background />
              <Controls />
            </ReactFlow>
          )}
        </div>
        <div className="actions">
          <button type="button" className="btn secondary" disabled={!Object.keys(moved).length || persist.isPending} onClick={() => persist.mutate()}>Save layout</button>
          <button type="button" className="btn secondary" disabled={suggestions.isPending || nodes.length === 0} onClick={() => suggestions.mutate()}>Suggest connections</button>
        </div>
        <Notice error={persist.error ?? suggestions.error} ok={notice} />
        {suggestions.data ? <Suggestions data={suggestions.data} onDone={async () => { suggestions.reset(); await refresh() }} /> : null}
        <div className="split">
          <AddInterest onDone={refresh} />
          {current ? <NodeEditor node={current} nodes={graph.data?.nodes ?? []} onDone={async () => { setSelected(null); await refresh() }} /> : <p className="empty">Select a node to edit it, or use the list.</p>}
        </div>
        <InterestList nodes={graph.data?.nodes ?? []} edges={graph.data?.edges ?? []} onSelect={setSelected} onDone={refresh} />
      </QueryState>
    </section>
  )
}

function InterestNode({ data }: NodeProps) {
  const node = data as unknown as GraphNode
  return (
    <div className={`gnode ${node.node_kind} type-${node.interest_type}`}>
      <strong>{node.name}</strong>
      <small>{labelize(node.node_kind)} · {labelize(node.interest_type)}</small>
      {node.course_progress_percent !== null ? <small>Course progress {node.course_progress_percent}%</small> : null}
    </div>
  )
}

function layout(nodes: GraphNode[], moved: Record<string, { x: number; y: number }>): Node[] {
  return nodes.map((node, index) => ({
    id: node.id,
    type: 'interest',
    data: node,
    position: moved[node.id] ?? node.position ?? { x: (index % 4) * 240, y: Math.floor(index / 4) * 150 },
  }))
}

function AddInterest({ onDone }: { onDone: () => Promise<void> }) {
  const [name, setName] = useState('')
  const [interestType, setType] = useState('personal')
  const [nodeKind, setKind] = useState('secondary')
  const create = useMutation({
    mutationFn: () => createInterest({ name, interest_type: interestType, node_kind: nodeKind }),
    onSuccess: async () => { setName(''); await onDone() },
  })
  return (
    <form className="panel stack-form" onSubmit={(event: FormEvent) => { event.preventDefault(); create.mutate() }}>
      <header className="panel-header"><h2>Add an interest</h2></header>
      <label className="field"><span>Name</span><input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} /></label>
      <div className="row">
        <label className="field"><span>Type</span><TypeSelect value={interestType} onChange={setType} /></label>
        <label className="field"><span>Size</span>
          <select value={nodeKind} onChange={(e) => setKind(e.target.value)}>
            <option value="main">Main area</option><option value="secondary">Subfield</option><option value="skill">Skill</option>
          </select>
        </label>
      </div>
      <button type="submit" className="btn primary" disabled={create.isPending}>Add</button>
      <Notice error={create.error} />
    </form>
  )
}

function NodeEditor({ node, nodes, onDone }: { node: GraphNode; nodes: GraphNode[]; onDone: () => Promise<void> }) {
  const [name, setName] = useState(node.name)
  const [description, setDescription] = useState(node.description ?? '')
  const [seeks, setSeeks] = useState(node.seeks_income)
  const [target, setTarget] = useState('')
  const [kind, setKind] = useState('related_to')
  const save = useMutation({ mutationFn: () => updateInterest(node.id, { name, description, seeks_income: seeks }), onSuccess: onDone })
  const remove = useMutation({ mutationFn: () => deleteInterest(node.id), onSuccess: onDone })
  const connect = useMutation({
    mutationFn: () => createRelationship({ source_interest_id: node.id, target_interest_id: target, relationship_type: kind }),
    onSuccess: onDone,
  })
  return (
    <form className="panel stack-form" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
      <header className="panel-header"><h2>{node.name}</h2>
        <p>{node.course_count} pathways · {node.goal_count} goals · {node.evidence_count} finished projects. Progress is completed required modules.</p>
      </header>
      <label className="field"><span>Name</span><input required value={name} onChange={(e) => setName(e.target.value)} /></label>
      <label className="field"><span>Description</span><textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} /></label>
      <label className="check"><input type="checkbox" checked={seeks} onChange={(e) => setSeeks(e.target.checked)} /> I want to earn from this</label>
      <div className="actions">
        <button type="submit" className="btn primary" disabled={save.isPending}>Save</button>
        <button type="button" className="btn secondary" onClick={() => remove.mutate()}>Remove</button>
        <Link className="btn secondary" to={`/learn?interest=${node.id}`}>Pathways</Link>
      </div>
      <div className="row">
        <label className="field grow"><span>Connect to</span>
          <select value={target} onChange={(e) => setTarget(e.target.value)}>
            <option value="">Choose</option>
            {nodes.filter((other) => other.id !== node.id).map((other) => <option key={other.id} value={other.id}>{other.name}</option>)}
          </select>
        </label>
        <label className="field"><span>As</span><RelSelect value={kind} onChange={setKind} /></label>
        <button type="button" className="btn secondary" disabled={!target || connect.isPending} onClick={() => connect.mutate()}>Connect</button>
      </div>
      <Notice error={save.error ?? remove.error ?? connect.error} />
    </form>
  )
}

function Suggestions({ data, onDone }: { data: Awaited<ReturnType<typeof suggestInterests>>; onDone: () => Promise<void> }) {
  const acceptInterest = useMutation({
    mutationFn: (item: (typeof data.interests)[number]) => createInterest({
      name: item.name, interest_type: item.interest_type, node_kind: item.node_kind, source: 'suggestion',
      connect_to: item.connects_to, relationship_type: item.relationship_type,
    }),
    onSuccess: onDone,
  })
  const acceptLink = useMutation({
    mutationFn: (item: (typeof data.connections)[number]) => createRelationship(item),
    onSuccess: onDone,
  })
  if (!data.interests.length && !data.connections.length) return <p className="empty">No new suggestions. Your graph already covers the obvious links.</p>
  return (
    <div className="panel">
      <header className="panel-header"><h2>Suggestions</h2><p>These are ideas. Nothing is added until you accept it.</p></header>
      <ul className="plain">
        {data.interests.map((item) => (
          <li key={item.name}><span>{item.name} — {item.reason}</span>
            <button type="button" className="btn secondary" onClick={() => acceptInterest.mutate(item)}>Add</button></li>
        ))}
        {data.connections.map((item) => (
          <li key={`${item.source_interest_id}-${item.target_interest_id}`}><span>{labelize(item.relationship_type)}: {item.reason}</span>
            <button type="button" className="btn secondary" onClick={() => acceptLink.mutate(item)}>Connect</button></li>
        ))}
      </ul>
      <Notice error={acceptInterest.error ?? acceptLink.error} />
    </div>
  )
}

function InterestList({ nodes, edges, onSelect, onDone }: { nodes: GraphNode[]; edges: { id: string; relationship_type: string }[]; onSelect: (id: string) => void; onDone: () => Promise<void> }) {
  const removeEdge = useMutation({ mutationFn: deleteRelationship, onSuccess: onDone })
  return (
    <div className="panel">
      <header className="panel-header"><h2>List view</h2><p>The same graph, readable without the canvas.</p></header>
      <ul className="plain">
        {nodes.map((node) => (
          <li key={node.id}>
            <button type="button" className="link" onClick={() => onSelect(node.id)}>{node.name}</button>
            <span>{labelize(node.interest_type)} · priority {node.priority}{node.course_progress_percent !== null ? ` · ${node.course_progress_percent}%` : ''}</span>
          </li>
        ))}
      </ul>
      {edges.length ? <p className="empty">{edges.length} connections. <button type="button" className="link" onClick={() => removeEdge.mutate(edges[0].id)}>Remove the first</button></p> : null}
    </div>
  )
}

function TypeSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {['professional', 'creative', 'personal', 'educational', 'entrepreneurial'].map((type) => <option key={type} value={type}>{labelize(type)}</option>)}
    </select>
  )
}

function RelSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {['part_of', 'related_to', 'develops_into', 'shares_skills_with', 'supports', 'overlaps_with'].map((type) => <option key={type} value={type}>{labelize(type)}</option>)}
    </select>
  )
}
