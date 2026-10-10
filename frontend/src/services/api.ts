import { getEnv } from '../lib/env'
import type {
  ActivitySeries,
  ChatMessage,
  Conversation,
  ConversationSummary,
  CourseDetail,
  CourseSummary,
  DocumentDetail,
  DocumentRecord,
  EarningPlan,
  Goal,
  Graph,
  Interest,
  InterestAnalytics,
  JobSearch,
  OnboardingDraft,
  OnboardingStatus,
  Opportunity,
  Overview,
  SalaryReport,
  Suggestions,
} from '../types/domain'
import type { Profile, ProfileFact, ProfileUpdate } from '../types/profile'
import { getAccessToken } from './auth'

export class ApiError extends Error {
  status: number
  code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

type ErrorEnvelope = { error?: { code?: unknown; message?: unknown } }

async function toApiError(response: Response): Promise<ApiError> {
  let code = 'http_error'
  let message = response.statusText || `Request failed (${response.status})`
  try {
    const body = (await response.json()) as ErrorEnvelope
    if (typeof body.error?.code === 'string') code = body.error.code
    if (typeof body.error?.message === 'string') message = body.error.message
  } catch {
    // Not JSON: keep the status text.
  }
  return new ApiError(response.status, code, message)
}

/** Authenticated request to the PlotPlanner API. The identity comes from the Supabase session token. */
async function request<T>(path: string, init: RequestInit = {}, jsonBody = true): Promise<T> {
  const token = await getAccessToken()
  if (!token) throw new ApiError(401, 'authentication_required', 'You are signed out. Please sign in again.')

  const { apiBaseUrl } = getEnv()
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers: {
        ...(jsonBody ? { 'Content-Type': 'application/json' } : {}),
        ...(init.headers ?? {}),
        Authorization: `Bearer ${token}`,
      },
    })
  } catch {
    throw new ApiError(0, 'network_error', `Cannot reach the PlotPlanner API at ${apiBaseUrl}. Is the backend running?`)
  }

  if (!response.ok) throw await toApiError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

function send<T>(path: string, method: string, body?: unknown): Promise<T> {
  return request<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) })
}

export function getProfile(): Promise<Profile> {
  return request<Profile>('/profile')
}

export function updateProfile(changes: ProfileUpdate): Promise<Profile> {
  return send<Profile>('/profile', 'PATCH', changes)
}

export const listFacts = (confirmed?: boolean) =>
  request<ProfileFact[]>(`/profile/facts${confirmed === undefined ? '' : `?confirmed=${confirmed}`}`)
export const createFact = (body: { kind: string; value: string; detail?: string }) => send<ProfileFact>('/profile/facts', 'POST', body)
export const updateFact = (id: string, body: { value?: string; detail?: string | null; confirmed?: boolean }) =>
  send<ProfileFact>(`/profile/facts/${id}`, 'PATCH', body)
export const deleteFact = (id: string) => request<void>(`/profile/facts/${id}`, { method: 'DELETE' })

export const onboardingStatus = () => request<OnboardingStatus>('/onboarding/status')
export const startOnboarding = () => send<OnboardingStatus>('/onboarding/start', 'POST')
export const onboardingTurn = (message: string) => send<{ status: OnboardingStatus }>('/onboarding/turn', 'POST', { message })
export const retryOnboarding = () => send<OnboardingStatus>('/onboarding/retry', 'POST')
export const saveOnboardingDraft = (draft: OnboardingDraft) => send<OnboardingStatus>('/onboarding/draft', 'PUT', draft)
export const completeOnboarding = (draft: OnboardingDraft) =>
  send<{ interests_created: number; goals_created: number; relationships_created: number; courses_started: string[]; warnings: string[] }>(
    '/onboarding/complete',
    'POST',
    draft,
  )
export const skipOnboarding = () => request<void>('/onboarding/skip', { method: 'POST' })

export const listInterests = () => request<Interest[]>('/interests')
export const createInterest = (body: Record<string, unknown>) => send<Interest>('/interests', 'POST', body)
export const updateInterest = (id: string, body: Record<string, unknown>) => send<Interest>(`/interests/${id}`, 'PATCH', body)
export const deleteInterest = (id: string) => request<void>(`/interests/${id}`, { method: 'DELETE' })
export const getGraph = () => request<Graph>('/interests/graph')
export const saveLayout = (positions: { id: string; x: number; y: number }[]) => send<{ updated: number }>('/interests/layout', 'PUT', { positions })
export const suggestInterests = () => send<Suggestions>('/interests/suggestions', 'POST')
export const createRelationship = (body: { source_interest_id: string; target_interest_id: string; relationship_type: string }) =>
  send('/interests/relationships', 'POST', body)
export const deleteRelationship = (id: string) => request<void>(`/interests/relationships/${id}`, { method: 'DELETE' })

export const listGoals = () => request<Goal[]>('/goals')
export const createGoal = (body: Record<string, unknown>) => send<Goal>('/goals', 'POST', body)
export const updateGoal = (id: string, body: Record<string, unknown>) => send<Goal>(`/goals/${id}`, 'PATCH', body)
export const deleteGoal = (id: string) => request<void>(`/goals/${id}`, { method: 'DELETE' })
export const planGoal = (id: string, adjustment?: string) => send<Goal>(`/goals/${id}/plan`, 'POST', adjustment ? { adjustment } : {})
export const addMilestone = (id: string, title: string) => send<Goal>(`/goals/${id}/milestones`, 'POST', { title })
export const updateMilestone = (goalId: string, id: string, body: Record<string, unknown>) =>
  send<Goal>(`/goals/${goalId}/milestones/${id}`, 'PATCH', body)
export const deleteMilestone = (goalId: string, id: string) => request<Goal>(`/goals/${goalId}/milestones/${id}`, { method: 'DELETE' })
export const addCheckin = (id: string, body: { note?: string; minutes?: number }) => send<Goal>(`/goals/${id}/checkins`, 'POST', body)

export const listCourses = (interestId?: string) => request<CourseSummary[]>(`/courses${interestId ? `?interest_id=${interestId}` : ''}`)
export const getCourse = (id: string) => request<CourseDetail>(`/courses/${id}`)
export const generateCourse = (body: { interest_id?: string; goal_id?: string; topic?: string; focus?: string }) =>
  send<CourseDetail>('/courses/generate', 'POST', body)
export const regenerateCourse = (id: string, focus?: string) => send<CourseDetail>(`/courses/${id}/regenerate`, 'POST', focus ? { focus } : {})
export const enrollCourse = (id: string) => send<CourseDetail>(`/courses/${id}/enroll`, 'POST')
export const setEnrollment = (id: string, status: string) => send<CourseDetail>(`/courses/${id}/enrollment`, 'PATCH', { status })
export const leaveCourse = (id: string) => request<void>(`/courses/${id}/enrollment`, { method: 'DELETE' })
export const archiveCourse = (id: string) => request<void>(`/courses/${id}`, { method: 'DELETE' })
export const setActivity = (courseId: string, moduleId: string, body: { activity_id: string; completed: boolean; notes?: string }) =>
  send<CourseDetail>(`/courses/${courseId}/modules/${moduleId}/progress`, 'PATCH', body)
export const refreshResources = (courseId: string, moduleId: string) =>
  send<CourseDetail>(`/courses/${courseId}/modules/${moduleId}/resources/refresh`, 'POST')

export const searchJobs = (body: { query: string; location?: string; remote_only: boolean; assess_fit: boolean }) =>
  send<JobSearch>('/opportunities/search', 'POST', body)
export const listOpportunities = (status?: string) => request<Opportunity[]>(`/opportunities${status ? `?status=${status}` : ''}`)
export const saveOpportunity = (id: string) => send<Opportunity>(`/opportunities/${id}/save`, 'POST')
export const setOpportunityStatus = (id: string, body: { status: string; notes?: string }) =>
  send<Opportunity>(`/opportunities/${id}/status`, 'PATCH', body)
export const salaryReport = (body: { role: string; location?: string; remote_only: boolean }) => send<SalaryReport>('/opportunities/salary', 'POST', body)
export const createEarningPlan = (body: { interest_id?: string; kind?: string; focus?: string }) => send<EarningPlan>('/opportunities/plan', 'POST', body)
export const listEarningPlans = () => request<EarningPlan[]>('/opportunities/plans')
export const deleteEarningPlan = (id: string) => request<void>(`/opportunities/plans/${id}`, { method: 'DELETE' })

export const listConversations = () => request<ConversationSummary[]>('/chat/conversations')
export const getConversation = (id: string) => request<Conversation>(`/chat/conversations/${id}`)
export const sendChat = (message: string, conversationId?: string) =>
  send<Conversation>('/chat', 'POST', { message, conversation_id: conversationId ?? null })
export const retryChat = (id: string) => send<Conversation>(`/chat/conversations/${id}/retry`, 'POST')
export const deleteConversation = (id: string) => request<void>(`/chat/conversations/${id}`, { method: 'DELETE' })
export const decideProposal = (messageId: string, index: number, accept: boolean) =>
  send<ChatMessage>(`/chat/messages/${messageId}/proposals/${index}`, 'POST', { accept })

export const listDocuments = () => request<DocumentRecord[]>('/documents')
export const getDocument = (id: string) => request<DocumentDetail>(`/documents/${id}`)
export function uploadDocument(file: File): Promise<DocumentDetail> {
  const body = new FormData()
  body.append('file', file)
  return request<DocumentDetail>('/documents', { method: 'POST', body }, false)
}
export const deleteDocument = (id: string) => request<void>(`/documents/${id}`, { method: 'DELETE' })

export const getOverview = () => request<Overview>('/analytics/overview')
export const getInterestAnalytics = () => request<InterestAnalytics>('/analytics/interests')
export const getActivity = (days = 84) => request<ActivitySeries>(`/analytics/activity?days=${days}`)

export const deleteAccountData = () => send<{ deleted: boolean; auth_account_deleted: boolean; note: string }>('/account/delete-data', 'POST', { confirm: 'DELETE' })
