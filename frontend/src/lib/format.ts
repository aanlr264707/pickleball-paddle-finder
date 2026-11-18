import type { Metric, MetricKey } from '../api/types'

/** 116 -> "116", 7.96 -> "7.96", 2101 -> "2,101". Missing values become an en dash. */
export function formatNumber(value: number | null | undefined, maxDigits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '–'
  return value.toLocaleString('en-US', { maximumFractionDigits: maxDigits })
}

export function formatPrice(value: number | null | undefined): string {
  if (value === null || value === undefined) return '–'
  return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

/** A metric value with its unit: "$199.99", "7.96 oz", "56.6 MPH", "116". */
export function formatMetric(metric: Pick<Metric, 'key' | 'unit'>, value: number | null | undefined): string {
  if (value === null || value === undefined) return '–'
  if (metric.key === 'price') return formatPrice(value)
  const number = formatNumber(value, metric.key === 'grip_size' ? 3 : 2)
  return metric.unit === 'units' ? number : `${number} ${metric.unit}`
}

/** "Control +" -> "Control". Groups the six paddle types into three families. */
export type Family = 'Control' | 'All-Court' | 'Power'

export function paddleFamily(paddleType: string): Family {
  if (paddleType.startsWith('Power')) return 'Power'
  if (paddleType.startsWith('All-Court')) return 'All-Court'
  return 'Control'
}

/** Ordinal suffix for a percentile: 1 -> "1st", 22 -> "22nd", 13 -> "13th". */
export function ordinal(n: number): string {
  const tens = n % 100
  if (tens >= 11 && tens <= 13) return `${n}th`
  return `${n}${({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[n % 10] ?? 'th'}`
}

/** Slider step for a metric: about a hundredth of its range, rounded to a power of ten. */
export function stepFor(metric: Pick<Metric, 'min' | 'max'>): number {
  const range = metric.max - metric.min
  if (range <= 0) return 1
  return 10 ** (Math.floor(Math.log10(range)) - 2)
}

/** Round to the precision of a step (avoids 7.960000000001). */
export function roundToStep(value: number, step: number): number {
  const decimals = Math.max(0, -Math.floor(Math.log10(step)))
  return Number(value.toFixed(decimals))
}

/** Where a value sits on a metric's min..max scale, 0 to 100. */
export function positionOnScale(metric: Pick<Metric, 'min' | 'max'>, value: number): number {
  if (metric.max === metric.min) return 50
  return Math.min(100, Math.max(0, ((value - metric.min) / (metric.max - metric.min)) * 100))
}

export const RESULT_METRICS: MetricKey[] = ['weight', 'swing_weight', 'twist_weight', 'power', 'pop', 'spin']
