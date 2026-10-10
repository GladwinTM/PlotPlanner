import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Notice, QueryState, labelize } from '../components/ui'
import { generateCourse, listCourses, listInterests } from '../services/api'

export function CoursesPage() {
  const [params] = useSearchParams()
  const interestId = params.get('interest') ?? undefined
  const client = useQueryClient()
  const courses = useQuery({
    queryKey: ['courses', interestId ?? 'all'],
    queryFn: () => listCourses(interestId),
    retry: false,
    refetchInterval: (query) => (query.state.data?.some((course) => course.status === 'generating') ? 2500 : false),
  })
  const interests = useQuery({ queryKey: ['interests'], queryFn: listInterests })
  const [topic, setTopic] = useState('')
  const [chosen, setChosen] = useState(interestId ?? '')
  const [focus, setFocus] = useState('')
  const generate = useMutation({
    mutationFn: () => generateCourse({ interest_id: chosen || undefined, topic: topic || undefined, focus: focus || undefined }),
    onSuccess: async () => { setTopic(''); setFocus(''); await client.invalidateQueries({ queryKey: ['courses'] }) },
  })

  return (
    <section className="page">
      <header className="page-head">
        <p className="eyebrow">Learning pathways</p>
        <h1>Learn it in pieces you can finish.</h1>
        <p>Each pathway is generated for you, then filled with videos and docs that were checked at the time they were added.</p>
      </header>
      <form className="panel stack-form" onSubmit={(event: FormEvent) => { event.preventDefault(); generate.mutate() }}>
        <header className="panel-header"><h2>New pathway</h2></header>
        <div className="row">
          <label className="field grow"><span>From an interest</span>
            <select value={chosen} onChange={(e) => setChosen(e.target.value)}>
              <option value="">None</option>
              {(interests.data ?? []).map((interest) => <option key={interest.id} value={interest.id}>{interest.name}</option>)}
            </select>
          </label>
          <label className="field grow"><span>Or a topic</span><input value={topic} maxLength={200} onChange={(e) => setTopic(e.target.value)} placeholder="Songwriting" /></label>
        </div>
        <label className="field"><span>Focus (optional)</span><input value={focus} maxLength={500} onChange={(e) => setFocus(e.target.value)} placeholder="I already know the basics" /></label>
        <button type="submit" className="btn primary" disabled={generate.isPending || (!chosen && topic.trim().length < 2)}>
          {generate.isPending ? 'Starting…' : 'Generate pathway'}
        </button>
        <Notice error={generate.error} />
      </form>
      <QueryState pending={courses.isPending} error={courses.error} onRetry={() => void courses.refetch()} empty={<p className="empty">No pathways yet.</p>}>
        <div className="cards">
          {(courses.data ?? []).map((course) => (
            <Link key={course.id} className="card" to={`/learn/${course.id}`}>
              <p className="eyebrow">{course.interest_name ?? 'Topic'} · {labelize(course.difficulty)}</p>
              <h2>{course.title}</h2>
              <p>{course.objective ?? course.description}</p>
              <p className="meta">
                {course.status === 'generating' ? 'Generating…' : course.status === 'failed' ? course.error : (
                  <>{course.estimated_hours ?? '?'} h · {course.progress.percent}% · {course.next_activity ? `Next: ${course.next_activity.activity_title}` : course.enrollment?.status ?? 'Not enrolled'}</>
                )}
              </p>
            </Link>
          ))}
        </div>
      </QueryState>
    </section>
  )
}
