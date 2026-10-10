import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Notice, QueryState, labelize } from '../components/ui'
import { archiveCourse, enrollCourse, getCourse, leaveCourse, refreshResources, regenerateCourse, setActivity, setEnrollment } from '../services/api'

export function CoursePage() {
  const { courseId = '' } = useParams()
  const client = useQueryClient()
  const course = useQuery({
    queryKey: ['course', courseId],
    queryFn: () => getCourse(courseId),
    retry: false,
    refetchInterval: (query) => (query.state.data?.status === 'generating' ? 2500 : false),
  })
  const refresh = () => client.invalidateQueries({ queryKey: ['course', courseId] })
  const act = useMutation({ mutationFn: (fn: () => Promise<unknown>) => fn(), onSuccess: refresh })
  const [focus, setFocus] = useState('')
  const [notes, setNotes] = useState<Record<string, string>>({})

  return (
    <section className="page">
      <Link to="/learn" className="link">All pathways</Link>
      <QueryState pending={course.isPending} error={course.error} onRetry={() => void course.refetch()}>
        {course.data ? (
          <>
            <header className="page-head">
              <p className="eyebrow">{course.data.interest_name ?? 'Pathway'} · version {course.data.version} · {labelize(course.data.status)}</p>
              <h1>{course.data.title}</h1>
              <p>{course.data.description}</p>
              {course.data.objective ? <p><strong>You'll be able to: </strong>{course.data.objective}</p> : null}
              {course.data.prerequisites ? <p className="empty">Before you start: {course.data.prerequisites}</p> : null}
              {course.data.error ? <p className="toast err" role="status">{course.data.error}</p> : null}
            </header>
            <p className="meta">
              {course.data.progress.completed_required_modules}/{course.data.progress.required_modules} required modules
              {' '}({course.data.progress.percent}%). Optional modules: {course.data.progress.completed_optional_modules}/{course.data.progress.optional_modules}.
              {' '}{course.data.estimated_hours ?? '?'} hours estimated.
            </p>
            <div className="actions">
              {!course.data.enrollment && course.data.status === 'ready' ? <button type="button" className="btn primary" onClick={() => act.mutate(() => enrollCourse(courseId))}>Enroll</button> : null}
              {course.data.enrollment?.status === 'active' ? <button type="button" className="btn secondary" onClick={() => act.mutate(() => setEnrollment(courseId, 'paused'))}>Pause</button> : null}
              {course.data.enrollment && course.data.enrollment.status !== 'active' && course.data.enrollment.status !== 'completed' ? <button type="button" className="btn primary" onClick={() => act.mutate(() => setEnrollment(courseId, 'active'))}>Resume</button> : null}
              {course.data.enrollment ? <button type="button" className="btn secondary" onClick={() => act.mutate(() => leaveCourse(courseId))}>Leave (keeps progress)</button> : null}
              <button type="button" className="btn secondary" onClick={() => act.mutate(() => archiveCourse(courseId))}>Archive</button>
            </div>
            {course.data.status === 'ready' || course.data.status === 'failed' ? (
              <form className="inline-form" onSubmit={(e) => { e.preventDefault(); act.mutate(() => regenerateCourse(courseId, focus || undefined)) }}>
                <label className="field grow"><span>Regenerate with a new focus</span><input value={focus} onChange={(e) => setFocus(e.target.value)} placeholder="Shorter, more practical" /></label>
                <button type="submit" className="btn secondary">New version</button>
              </form>
            ) : null}
            <Notice error={act.error} />
            {course.data.modules.map((module) => (
              <article key={module.id} className="panel">
                <header className="panel-header">
                  <h2>{module.position + 1}. {module.title} {module.required ? '' : '(optional)'}</h2>
                  <p>{module.description}</p>
                </header>
                {module.learning_objectives ? <p><strong>Learn: </strong>{module.learning_objectives}</p> : null}
                {module.completion_criteria ? <p className="empty">Done when: {module.completion_criteria}</p> : null}
                <ul className="activities">
                  {module.activities.map((activity) => (
                    <li key={activity.id}>
                      <label className="check">
                        <input type="checkbox" checked={activity.completed} disabled={!course.data?.enrollment || course.data.enrollment.status === 'paused'}
                          onChange={(e) => act.mutate(() => setActivity(courseId, module.id, { activity_id: activity.id, completed: e.target.checked, notes: notes[activity.id] }))} />
                        <span><strong>{activity.title}</strong> · {labelize(activity.kind)}{activity.estimated_minutes ? ` · ${activity.estimated_minutes} min` : ''}</span>
                      </label>
                      {activity.instructions ? <p>{activity.instructions}</p> : null}
                      {activity.kind === 'project' || activity.kind === 'reflection' ? (
                        <label className="field"><span>{activity.kind === 'project' ? 'Submission' : 'Reflection'}</span>
                          <textarea rows={2} defaultValue={activity.notes ?? ''} onChange={(e) => setNotes((n) => ({ ...n, [activity.id]: e.target.value }))} />
                        </label>
                      ) : null}
                    </li>
                  ))}
                </ul>
                <h3>Resources</h3>
                {module.resources.length === 0 ? <p className="empty">No verified resources for this module{module.resource_query ? ` (searched “${module.resource_query}”)` : ''}.</p> : (
                  <ul className="plain">
                    {module.resources.map((resource) => (
                      <li key={resource.id}>
                        <a href={resource.canonical_url} target="_blank" rel="noreferrer">{resource.title}</a>
                        <span>{resource.provider}{resource.channel ? ` · ${resource.channel}` : ''} · {labelize(resource.cost_status)} · {labelize(resource.verification_status)}{resource.duration_seconds ? ` · ${Math.round(resource.duration_seconds / 60)} min` : ''}</span>
                      </li>
                    ))}
                  </ul>
                )}
                <button type="button" className="btn secondary" onClick={() => act.mutate(() => refreshResources(courseId, module.id))}>Refresh videos</button>
              </article>
            ))}
          </>
        ) : null}
      </QueryState>
    </section>
  )
}
