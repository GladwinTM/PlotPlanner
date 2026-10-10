export type OnboardingDraft = {
  profile: {
    display_name: string | null
    location: string | null
    current_occupation: string | null
    education_summary: string | null
    experience_summary: string | null
    available_hours_per_week: number | null
    learning_preferences: string | null
    constraints_summary: string | null
  }
  interests: DraftInterest[]
  goals: DraftGoal[]
  skills: string[]
}

export type DraftInterest = {
  name: string
  description: string | null
  interest_type: string
  node_kind: string
  category: string | null
  priority: number
  seeks_income: boolean
  parent: string | null
}

export type DraftGoal = {
  title: string
  category: string
  target_outcome: string | null
  priority: number
  hours_per_week: number | null
}

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  meta: {
    tools_used?: string[]
    sources?: { kind: string; title: string; url: string; provider?: string; channel?: string; salary?: string | null }[]
    proposals?: Proposal[]
    scripted?: boolean
    assessment?: string
  }
  created_at: string
}

export type Proposal = {
  change_type: 'add_interest' | 'create_goal' | 'update_weekly_hours'
  name: string | null
  category: string | null
  interest_type: string | null
  hours: number | null
  reason: string
  status: 'pending' | 'accepted' | 'dismissed'
  result: string | null
}

export type OnboardingStatus = {
  completed: boolean
  conversation_id: string | null
  messages: ChatMessage[]
  draft: OnboardingDraft
  ready_to_finish: boolean
  awaiting_reply: boolean
  ai_configured: boolean
}

export type Interest = {
  id: string
  name: string
  description: string | null
  category: string | null
  interest_type: string
  node_kind: string
  priority: number
  source: string
  confidence: number | null
  seeks_income: boolean
  position_x: number | null
  position_y: number | null
  created_at: string
  updated_at: string
}

export type GraphNode = {
  id: string
  name: string
  description: string | null
  category: string | null
  interest_type: string
  node_kind: string
  priority: number
  source: string
  confidence: number | null
  seeks_income: boolean
  position: { x: number; y: number } | null
  course_count: number
  course_progress_percent: number | null
  goal_count: number
  evidence_count: number
}

export type GraphEdge = { id: string; source: string; target: string; relationship_type: string }

export type Graph = { nodes: GraphNode[]; edges: GraphEdge[] }

export type Suggestions = {
  interests: { name: string; interest_type: string; node_kind: string; connects_to: string[]; relationship_type: string; reason: string }[]
  connections: { source_interest_id: string; target_interest_id: string; relationship_type: string; reason: string }[]
  generated_by: 'ai'
}

export type Milestone = {
  id: string
  title: string
  description: string | null
  position: number
  due_date: string | null
  completed_at: string | null
  source: string
}

export type Goal = {
  id: string
  title: string
  description: string | null
  category: string
  target_outcome: string | null
  priority: number
  status: string
  target_date: string | null
  hours_per_week: number | null
  interest_id: string | null
  plan_summary: string | null
  completed_at: string | null
  milestones: Milestone[]
  checkins: { id: string; note: string | null; minutes: number | null; created_at: string }[]
  progress_percent: number
  minutes_logged: number
}

export type Resource = {
  id: string
  title: string
  provider: string
  channel: string | null
  canonical_url: string
  resource_type: string
  cost_status: string
  duration_seconds: number | null
  published_at: string | null
  retrieved_at: string
  verification_status: string
}

export type Activity = {
  id: string
  position: number
  kind: string
  title: string
  instructions: string | null
  estimated_minutes: number | null
  completed: boolean
  completed_at: string | null
  notes: string | null
}

export type Module = {
  id: string
  position: number
  title: string
  description: string | null
  learning_objectives: string | null
  completion_criteria: string | null
  required: boolean
  completed: boolean
  activities: Activity[]
  resources: Resource[]
  resource_query: string | null
}

export type CourseProgress = {
  percent: number
  required_modules: number
  completed_required_modules: number
  optional_modules: number
  completed_optional_modules: number
  activities: number
  completed_activities: number
}

export type CourseSummary = {
  id: string
  title: string
  description: string | null
  objective: string | null
  interest_id: string | null
  interest_name: string | null
  goal_id: string | null
  difficulty: string
  estimated_hours: number | null
  status: string
  error: string | null
  version: number
  enrollment: { status: string; started_at: string; completed_at: string | null } | null
  progress: CourseProgress
  next_activity: { module_id: string; module_title: string; activity_id: string; activity_title: string; kind: string } | null
  module_count: number
}

export type CourseDetail = CourseSummary & { prerequisites: string | null; focus: string | null; modules: Module[] }

export type Opportunity = {
  id: string
  opportunity_type: string
  title: string
  company: string | null
  description: string | null
  source: string
  canonical_url: string
  location: string | null
  employment_type: string | null
  compensation_text: string | null
  compensation_basis: string | null
  published_at: string | null
  retrieved_at: string
  fit_level: string | null
  fit_reason: string | null
  status: string
  notes: string | null
}

export type JobSearch = {
  results: Opportunity[]
  providers: string[]
  provider_errors: Record<string, string>
  fit_assessed: boolean
  fit_note: string | null
  attribution: { name: string; url: string }[]
}

export type EarningPlan = { id: string; interest_id: string | null; title: string; kind: string; plan: Record<string, unknown>; created_at: string }

export type SalaryReport = {
  role: string
  listings_checked: number
  groups: { currency: string; period: string; basis: string; sample_size: number; low: number; median: number; high: number }[]
  evidence: { title: string; company: string | null; location: string | null; compensation_text: string; basis: string; source: string; url: string; retrieved_at: string }[]
  note: string
}

export type DocumentRecord = {
  id: string
  filename: string
  content_type: string
  size_bytes: number
  processing_status: string
  error: string | null
  created_at: string
  processed_at: string | null
}

export type DocumentDetail = DocumentRecord & { text_preview: string | null; text_length: number; facts: import('./profile').ProfileFact[] }

export type ConversationSummary = { id: string; title: string; created_at: string; updated_at: string; message_count: number }

export type Conversation = ConversationSummary & { messages: ChatMessage[] }

export type Overview = {
  active_interests: number
  active_courses: number
  completed_courses: number
  completed_modules: number
  completed_activities: number
  completed_projects: number
  active_goals: number
  completed_goals: number
  minutes_logged: number
  tracked_opportunities: number
  courses: { course_id: string; title: string; enrollment: string; percent: number }[]
  goals: { goal_id: string; title: string; status: string; percent: number }[]
  suggestions: { kind: string; message: string; course_id?: string; goal_id?: string; interest_id?: string }[]
  definitions: Record<string, string>
}

export type ActivitySeries = { days: number; series: { date: string; activities_completed: number; milestones_completed: number; checkins: number; minutes_logged: number; messages: number }[] }

export type InterestAnalytics = {
  interests: { id: string; name: string; interest_type: string; node_kind: string; priority: number; connections: number; enrolled_courses: number; average_course_percent: number | null; goals: number }[]
  by_type: { interest_type: string; count: number }[]
  note: string
}
