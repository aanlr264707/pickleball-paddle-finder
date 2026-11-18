import { createContext, useContext, type ReactNode } from 'react'
import { api } from '../api/client'
import type { Metric, MetricKey, Options, Preset } from '../api/types'
import { useApi } from './useApi'

export interface Reference {
  metrics: Metric[]
  metricsByKey: Record<MetricKey, Metric>
  options: Options
  presets: Preset[]
}

const ReferenceContext = createContext<Reference | null>(null)

async function loadReference(): Promise<Reference> {
  const [metrics, options, presets] = await Promise.all([api.metrics(), api.options(), api.presets()])
  const metricsByKey = Object.fromEntries(metrics.map((m) => [m.key, m])) as Record<MetricKey, Metric>
  return { metrics, metricsByKey, options, presets }
}

/** Loads the metric definitions, menu options and presets once for the whole app. */
export function ReferenceProvider({ children, fallback }: {
  children: ReactNode
  fallback: (state: { error: Error | null }) => ReactNode
}) {
  const { data, error } = useApi(loadReference, 'reference')
  if (!data) return <>{fallback({ error })}</>
  return <ReferenceContext.Provider value={data}>{children}</ReferenceContext.Provider>
}

export function useReference(): Reference {
  const reference = useContext(ReferenceContext)
  if (!reference) throw new Error('useReference must be used inside <ReferenceProvider>')
  return reference
}
