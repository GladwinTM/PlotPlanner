import type {
  DocumentCreate,
  DocumentRead,
  Profile,
  ProfileCreate,
  ProfileUpdate,
  SearchRequest,
  SearchResult,
} from './types'
import { getEnv } from '../lib/env'
import { getAccessToken } from '../services/auth'

const PROFILE_API = import.meta.env.VITE_PROFILE_API_URL ?? 'http://localhost:8000'
// Search is retained only for the legacy evidence panel; document ingestion uses
// the active authenticated API above.
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

/**
 * Compatibility bridge for the older text-ingestion panel.
 * The active API owns documents at /api/v1/documents and accepts multipart files;
 * keeping this adapter prevents the former knowledge-service /v1/documents 404.
 */
export async function createDocument(payload: DocumentCreate): Promise<DocumentRead> {
  const token = await getAccessToken()
  if (!token) throw new Error('You are signed out. Please sign in again.')
  const body = new FormData()
  body.append('file', new File([payload.content], `${payload.title.trim() || 'document'}.txt`, { type: 'text/plain' }))
  const { apiBaseUrl } = getEnv()
  const response = await fetch(`${apiBaseUrl}/documents`, { method: 'POST', body, headers: { Authorization: `Bearer ${token}` } })
  if (!response.ok) {
    let message = response.statusText || `Request failed (${response.status})`
    try {
      const data = (await response.json()) as { error?: { message?: string } }
      message = data.error?.message ?? message
    } catch { /* Keep the HTTP status text. */ }
    throw new Error(message)
  }
  const document = (await response.json()) as { id: string; filename: string; created_at: string }
  return {
    id: document.id,
    profile_id: payload.profile_id,
    title: document.filename,
    source_type: payload.source_type,
    source_uri: payload.source_uri ?? null,
    created_at: document.created_at,
    chunk_count: 0,
  }
}

export function searchEvidence(payload: SearchRequest) {
  return request<SearchResult[]>(`${KNOWLEDGE_API}/v1/search`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
