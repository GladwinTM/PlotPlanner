export type Profile = {
  id: string
  display_name: string
  bio: string | null
  interests: string[]
  goals: string[]
  created_at: string
  updated_at: string
}

export type ProfileCreate = {
  display_name: string
  bio?: string | null
  interests?: string[]
  goals?: string[]
}

export type ProfileUpdate = {
  display_name?: string
  bio?: string | null
  interests?: string[]
  goals?: string[]
}

export type SourceType = 'note' | 'resume' | 'portfolio' | 'job_description'

export type DocumentCreate = {
  profile_id: string
  title: string
  source_type: SourceType
  source_uri?: string | null
  content: string
}

export type DocumentRead = {
  id: string
  profile_id: string
  title: string
  source_type: SourceType
  source_uri: string | null
  created_at: string
  chunk_count: number
}

export type SearchRequest = {
  profile_id: string
  query: string
  limit?: number
}

export type SearchResult = {
  document_id: string
  document_title: string
  content: string
  score: number
}
