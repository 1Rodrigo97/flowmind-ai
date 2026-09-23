// Typed API client for the FlowMind AI backend.

const BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

export interface DocumentOut {
  id: number
  filename: string
  file_type: string
  size_bytes: number
  chunk_count: number
  status: string
  created_at: string
}

export interface UploadResult {
  document_id: number
  filename: string
  chunks: number
  status: string
  duplicate: boolean
}

export interface RetrievedChunk {
  document_id: number
  document: string
  section: string | null
  page: number | null
  excerpt: string
  score: number
}

export interface SearchResponse {
  query: string
  results: RetrievedChunk[]
}

export interface ChatResponse {
  answer: string
  sources: RetrievedChunk[]
  status: string
}

export interface StatsResponse {
  documents: number
  chunks: number
  file_types: Record<string, number>
  recent: DocumentOut[]
}

async function handle<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`
    try {
      const body = await resp.json()
      if (body?.detail) detail = body.detail
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail)
  }
  return resp.json() as Promise<T>
}

export const api = {
  base: BASE,

  async stats(): Promise<StatsResponse> {
    return handle(await fetch(`${BASE}/api/stats`))
  },

  async listDocuments(): Promise<DocumentOut[]> {
    return handle(await fetch(`${BASE}/api/documents`))
  },

  async uploadDocument(file: File): Promise<UploadResult> {
    const form = new FormData()
    form.append('file', file)
    return handle(await fetch(`${BASE}/api/documents/upload`, { method: 'POST', body: form }))
  },

  async deleteDocument(id: number): Promise<void> {
    const resp = await fetch(`${BASE}/api/documents/${id}`, { method: 'DELETE' })
    if (!resp.ok && resp.status !== 204) throw new Error(`Delete failed: ${resp.status}`)
  },

  async search(query: string, topK: number): Promise<SearchResponse> {
    return handle(
      await fetch(`${BASE}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k: topK }),
      }),
    )
  },

  async chat(question: string, topK: number): Promise<ChatResponse> {
    return handle(
      await fetch(`${BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, top_k: topK }),
      }),
    )
  },
}
