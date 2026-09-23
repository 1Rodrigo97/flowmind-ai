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
  rerank_score?: number | null
}

export interface SearchResponse {
  query: string
  results: RetrievedChunk[]
  reranker?: string | null
  original?: RetrievedChunk[] | null
}

export interface ExperimentConfig {
  name: string
  embedding_provider?: string
  embedding_model?: string
  chunk_size: number
  chunk_overlap: number
  top_k: number
  similarity_threshold: number
  reranker_enabled: boolean
  reranker_model?: string
  reranker_candidates?: number
}

export interface ExperimentMetrics {
  hit_at_k: number
  mrr: number
  precision_at_k: number
  recall_at_k: number
  expected_terms_match: number
  answer_rate: number
  correct_refusal_rate: number
  latency_retrieval_ms: number
  latency_llm_ms: number
  positives: number
  negatives: number
  top_k: number
}

export interface Experiment {
  id: number
  name: string
  index_profile: string
  dataset_name: string
  dataset_size: number
  config: Partial<ExperimentConfig>
  metrics: ExperimentMetrics
  commit_sha: string | null
  duration_ms: number
  created_at: string
}

export interface CompareResponse {
  experiments: { id: number; name: string; metrics: ExperimentMetrics }[]
  deltas: Record<string, Record<string, number>>
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

  async search(query: string, topK: number, reranker?: boolean): Promise<SearchResponse> {
    return handle(
      await fetch(`${BASE}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k: topK, reranker: reranker ?? null }),
      }),
    )
  },

  async listExperiments(): Promise<Experiment[]> {
    return handle(await fetch(`${BASE}/api/evaluation/experiments`))
  },

  async runExperiment(config: ExperimentConfig): Promise<Experiment> {
    return handle(
      await fetch(`${BASE}/api/evaluation/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config, dataset: 'default' }),
      }),
    )
  },

  async compareExperiments(ids: number[]): Promise<CompareResponse> {
    return handle(
      await fetch(`${BASE}/api/evaluation/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ experiment_ids: ids }),
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
