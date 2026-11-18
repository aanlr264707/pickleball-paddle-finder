import type {
  Filters, Insights, Metric, Options, PaddlePage, PaddleWithPercentiles, PreferenceInput, Preset,
  Recommendations, ScoredPaddle,
} from './types'

const BASE = `${import.meta.env.VITE_API_URL ?? ''}/api`

/** An error response from the API, with the field that caused it when there is one. */
export class ApiError extends Error {
  readonly status: number
  readonly field?: string

  constructor(message: string, status: number, field?: string) {
    super(message)
    this.status = status
    this.field = field
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(BASE + path, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError("Can't reach the API. Check that the backend is running.", 0)
  }
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const error = body?.error
    throw new ApiError(error?.message ?? response.statusText, response.status, error?.field)
  }
  return body as T
}

/** Build a query string, leaving out empty values. */
export function toQuery(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '' || value === false) continue
    search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

export interface RecommendationRequest {
  filters: Filters
  preferences: PreferenceInput[]
  limit?: number
}

export const api = {
  metrics: () => request<Metric[]>('/metrics'),
  options: () => request<Options>('/options'),
  presets: () => request<Preset[]>('/presets'),
  recommend: (body: RecommendationRequest) =>
    request<Recommendations>('/recommendations', { method: 'POST', body: JSON.stringify(body) }),
  paddles: (params: Record<string, string | number | boolean | null | undefined>) =>
    request<PaddlePage>(`/paddles${toQuery(params)}`),
  paddle: (id: number) => request<PaddleWithPercentiles>(`/paddles/${id}`),
  similar: (id: number, limit = 6) => request<ScoredPaddle[]>(`/paddles/${id}/similar?limit=${limit}`),
  compare: (ids: number[]) => request<PaddleWithPercentiles[]>(`/compare?ids=${ids.join(',')}`),
  insights: () => request<Insights>('/insights'),
}
