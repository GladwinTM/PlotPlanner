import type {
  DocumentCreate,
  DocumentRead,
  Profile,
  ProfileCreate,
  ProfileUpdate,
  SearchRequest,
  SearchResult,
} from './types'

const PROFILE_API = import.meta.env.VITE_PROFILE_API_URL ?? 'http://localhost:8000'
const KNOWLEDGE_API = import.meta.env.VITE_KNOWLEDGE_API_URL ?? 'http://localhost:8002'

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') {
        detail = body.detail
      } else if (body.detail !== undefined) {
        detail = JSON.stringify(body.detail)
      }
    } catch {
      // keep statusText
    }
    throw new Error(detail || `Request failed (${response.status})`)
  }

  return (await response.json()) as T
}

export function createProfile(payload: ProfileCreate) {
  return request<Profile>(`${PROFILE_API}/v1/profiles`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getProfile(profileId: string) {
  return request<Profile>(`${PROFILE_API}/v1/profiles/${profileId}`)
}

export function updateProfile(profileId: string, payload: ProfileUpdate) {
  return request<Profile>(`${PROFILE_API}/v1/profiles/${profileId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function createDocument(payload: DocumentCreate) {
  return request<DocumentRead>(`${KNOWLEDGE_API}/v1/documents`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function searchEvidence(payload: SearchRequest) {
  return request<SearchResult[]>(`${KNOWLEDGE_API}/v1/search`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
