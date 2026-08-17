const API_BASE = '/api'

async function fetchJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export interface SlotStatus {
  name: string
  vendor: string
  model: string
  is_real: boolean
  is_mock: boolean
  is_reachable: boolean | null
  key_present: boolean
  base_url: string | null
}

export interface QuestionItem {
  id: string
  type: string
  priestley_area: string
  jurisdiction: string[]
  difficulty: string
  marks: number
}

export interface QuestionDetail extends QuestionItem {
  question_text: string
  facts: string | null
  instructions: string | null
  gold_answer: string
  required_authorities: Array<{ kind: string; cite: string; point_in_time?: string }>
  rubric: Array<{ criterion: string; max: number }>
  topics: string[]
  canary: string
}

export interface RunConfig {
  models: string[]
  n_reps: number
  base_seed: number
  question_filter?: string
  priestley_filter?: string
  jurisdiction_filter?: string
  difficulty_filter?: string
}

export interface ModelProgress {
  name: string
  is_mock: boolean
  n_done: number
  n_total: number
  n_ok: number
  n_error: number
  status: 'pending' | 'running' | 'done' | 'error'
}

export interface RunStatus {
  run_id: string
  status: 'running' | 'done' | 'error'
  n_completions: number
  n_total: number
  n_ok: number
  n_error: number
  models: ModelProgress[]
  started_at: string | null
  finished_at: string | null
  error_msg: string | null
}

export interface CitationAudit {
  kind: 'case' | 'statute'
  raw: string
  classification: 'on_point' | 'known_other' | 'fabricated'
}

export interface ItemResult {
  run_id: string
  model: string
  item_id: string
  rep: number
  is_mock: boolean
  priestley_area: string
  difficulty: string
  item_score_100: number
  fabricated_rate: number
  on_point_rate: number
  total_citations: number
  citations: CitationAudit[]
  rubric: Record<string, number>
  answer_text: string | null
  contamination_flag: boolean
}

export interface LeaderboardModel {
  model: string
  is_mock: boolean
  n_questions: number
  mean_item_score_100: { point: number; ci95: [number, number] }
  fabricated_rate: { point: number; ci95: [number, number] }
  per_difficulty: Record<string, { n: number; mean_item_score_100: number }>
  per_priestley: Record<string, { n: number; mean_item_score_100: number }>
}

export interface PairwiseResult {
  a: string
  b: string
  n_pairs: number
  mean_diff: number
  p_value: number
  significant_05: boolean
}

export interface StatsReport {
  run_id: string
  n_questions_total: number
  n_models: number
  models: LeaderboardModel[]
  pairwise_permutation: PairwiseResult[]
  method: Record<string, unknown>
}

export interface RunSummary {
  run_id: string
  started_at: string
  finished_at: string
  n_models: number
  n_items: number
  n_reps: number
  n_completions: number
  n_ok: number
  n_error: number
  models: string[]
}

// --- API calls ---

export const api = {
  health: () => fetchJson<{ status: string }>('/health'),

  getSlots: () => fetchJson<SlotStatus[]>('/slots'),

  getQuestions: () => fetchJson<QuestionItem[]>('/questions'),

  getQuestion: (id: string) => fetchJson<QuestionDetail>(`/questions/${id}`),

  getKeys: () => fetchJson<{ openai_key: string | null; anthropic_key: string | null; google_key: string | null; local_base_url: string; local_model: string; local_enable_thinking: boolean }>('/keys'),

  setKeys: (cfg: { openai_key?: string; anthropic_key?: string; google_key?: string; local_base_url?: string; local_model?: string; local_enable_thinking?: boolean }) =>
    fetchJson<{ status: string }>('/keys', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cfg) }),

  testConnection: (provider: string) =>
    fetchJson<{ ok: boolean; detail: string; model_id?: string }>(`/keys/test/${provider}`, { method: 'POST' }),

  createRun: (cfg: RunConfig) =>
    fetchJson<{ run_id: string }>('/runs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cfg) }),

  getRunStatus: (runId: string) => fetchJson<RunStatus>(`/runs/${runId}/status`),

  streamRun: (runId: string, onEvent: (event: { type: string; count?: number; total?: number }) => void, onComplete?: () => void) => {
    const es = new EventSource(`/api/runs/${runId}/stream`)
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        onEvent(data)
      } catch { /* ignore */ }
    }
    es.addEventListener('done', () => {
      onComplete?.()
      es.close()
    })
    return es
  },

  listRuns: () => fetchJson<RunSummary[]>('/runs'),

  getReport: (runId: string) => fetchJson<StatsReport>(`/runs/${runId}/report`),

  getItemResults: (runId: string, model?: string, question?: string) =>
    fetchJson<ItemResult[]>(`/runs/${runId}/item-results?${new URLSearchParams({ model: model ?? '', question: question ?? '' }).toString()}`),

  getRecords: (runId: string) => fetchJson<Array<Record<string, unknown>>>(`/runs/${runId}/records`),

  probeLocal: () => fetchJson<{ reachable: boolean; models: Array<Record<string, unknown>>; error?: string }>('/local/probe'),

  exportSite: (runId: string) => fetchJson<{ site_path: string }>(`/runs/${runId}/export-site`, { method: 'POST' }),

  exportHf: (runId: string) => fetchJson<{ export_path: string; n_items: number; files: string }>(`/runs/${runId}/export-hf`, { method: 'POST' }),

  downloadRun: (runId: string) => fetchJson<{ run_dir: string; meta: string; records: string; raw_dir: string }>(`/runs/${runId}/download`),
}
