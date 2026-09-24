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
  category?: string | null
  tags?: string[] | null
  has_insights?: boolean
}

export interface TaskItem {
  text: string
  due_date: string | null
}

export interface Insights {
  document_id: number
  summary: string
  category: string
  tags: string[]
  tasks: TaskItem[]
  dates: string[]
  model: string
  status: string
  created_at: string
}

export interface AutomationRun {
  id: number
  run_uid: string
  workflow: string
  filename: string
  document_id: number | null
  file_hash: string | null
  status: string
  insights_status: string | null
  attempts: number
  error_message: string | null
  duration_ms: number | null
  started_at: string
  finished_at: string | null
}

export interface AutomationStats {
  processed: number
  success: number
  duplicate: number
  failed: number
  pending: number
  avg_duration_ms: number
  tasks_extracted: number
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
  automated_today: number
  tasks_extracted: number
  automation_failures: number
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

  async getInsights(documentId: number): Promise<Insights | null> {
    const resp = await fetch(`${BASE}/api/documents/${documentId}/insights`)
    if (resp.status === 404) return null
    return handle(resp)
  },

  async generateInsights(documentId: number): Promise<Insights> {
    return handle(
      await fetch(`${BASE}/api/documents/${documentId}/insights`, { method: 'POST' }),
    )
  },

  async listRuns(): Promise<AutomationRun[]> {
    return handle(await fetch(`${BASE}/api/automation/runs`))
  },

  async automationStats(): Promise<AutomationStats> {
    return handle(await fetch(`${BASE}/api/automation/stats`))
  },

  async retryRun(runId: number): Promise<AutomationRun> {
    return handle(
      await fetch(`${BASE}/api/automation/runs/${runId}/retry`, { method: 'POST' }),
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
