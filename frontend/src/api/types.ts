// Shapes of the JSON returned by the Flask API (backend/paddle_finder/api/serializers.py).

export type MetricKey =
  | 'price' | 'weight' | 'swing_weight' | 'twist_weight' | 'power' | 'pop'
  | 'spin' | 'balance' | 'core' | 'grip_length' | 'grip_size'

export type Level = 'low' | 'medium' | 'high'

export interface Paddle {
  id: number
  brand: string
  name: string
  full_name: string
  link: string
  year: number | null
  approval: string
  shape: string
  face: string
  grit: string
  build: string
  paddle_type: string
  feel: string
  spin_rating: string
  spin_durability: string
  price: number | null
  weight: number | null
  swing_weight: number | null
  twist_weight: number | null
  power: number | null
  pop: number | null
  spin: number | null
  balance: number | null
  core: number | null
  grip_length: number | null
  grip_size: number | null
  tournament_legal: boolean
}

export interface Metric {
  key: MetricKey
  label: string
  unit: string
  description: string
  in_questionnaire: boolean
  count: number
  min: number
  max: number
  average: number
  percentiles: Record<'10' | '20' | '50' | '80' | '90', number>
}

export interface Options {
  brand: string[]
  shape: string[]
  paddle_type: string[]
  feel: string[]
}

export interface PresetTarget {
  metric: MetricKey
  label: string
  target: Level | number
  importance: number
}

export interface Preset {
  slug: string
  name: string
  description: string
  targets: PresetTarget[]
}

export interface Filters {
  max_price: number | null
  tournament_only: boolean
  shape: string | null
  paddle_type: string | null
  feel: string | null
}

export interface PreferenceInput {
  metric: MetricKey
  target: Level | number
  importance: number
}

export interface Fit {
  metric: MetricKey
  similarity: number
  value: number | null
}

export interface ScoredPaddle {
  rank: number
  score: number
  best_fit: MetricKey | null
  worst_fit: MetricKey | null
  fits: Fit[]
  paddle: Paddle
}

export interface Recommendations {
  candidates: number
  ranked: boolean
  preset: string | null
  preferences: { metric: MetricKey; label: string; target: number; importance: number }[]
  results: ScoredPaddle[]
}

export interface PaddlePage {
  items: Paddle[]
  total: number
  page: number
  per_page: number
  pages: number
}

export type Percentiles = Partial<Record<MetricKey, number>>

export interface PaddleWithPercentiles {
  paddle: Paddle
  percentiles: Percentiles
}

export interface Insights {
  summary: {
    paddles: number
    brands: number
    median_price: number
    min_price: number
    max_price: number
    newest_year: number
    usap_share: number
  }
  by_type: ({ paddle_type: string; count: number } & Record<string, number | string | null>)[]
  by_shape: { value: string; count: number }[]
  top_brands: { value: string; count: number }[]
  power_drivers: { metric: MetricKey; label: string; correlation: number }[]
  price_vs_power: { id: number; brand: string; name: string; price: number; power: number; paddle_type: string }[]
}
