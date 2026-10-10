export type Profile = {
  user_id: string
  display_name: string
  location: string | null
  current_occupation: string | null
  education_summary: string | null
  experience_summary: string | null
  available_hours_per_week: number | null
  learning_preferences: string | null
  constraints_summary: string | null
  onboarding_completed: boolean
  created_at: string
  updated_at: string
}

/** Editable fields only. `user_id` and `onboarding_completed` are server-controlled. */
export type ProfileUpdate = Partial<
  Pick<
    Profile,
    | 'display_name'
    | 'location'
    | 'current_occupation'
    | 'education_summary'
    | 'experience_summary'
    | 'available_hours_per_week'
    | 'learning_preferences'
    | 'constraints_summary'
  >
>

export type ProfileFact = {
  id: string
  kind: string
  value: string
  detail: string | null
  source: string
  document_id: string | null
  confirmed: boolean
  created_at: string
}
