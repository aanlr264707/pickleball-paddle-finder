import type { Level, Metric } from '../api/types'
import { formatMetric, positionOnScale, roundToStep, stepFor } from '../lib/format'

export interface MetricChoice {
  enabled: boolean
  value: number
  level: Level | null
  importance: number
}

const LEVELS: { level: Level; label: string; percentile: '20' | '50' | '80' }[] = [
  { level: 'low', label: 'Low', percentile: '20' },
  { level: 'medium', label: 'Medium', percentile: '50' },
  { level: 'high', label: 'High', percentile: '80' },
]
const IMPORTANCE = [1, 2, 3, 4, 5]

export function defaultChoice(metric: Metric): MetricChoice {
  return { enabled: false, value: metric.percentiles['50'], level: null, importance: 3 }
}

/** One questionnaire row: drag the ball along the line to set a target, then say how much it matters. */
export function TargetRail({ metric, choice, onChange }: {
  metric: Metric
  choice: MetricChoice
  onChange: (choice: MetricChoice) => void
}) {
  const step = stepFor(metric)
  const id = `target-${metric.key}`
  const set = (patch: Partial<MetricChoice>) => onChange({ ...choice, ...patch })

  return (
    <fieldset className={choice.enabled ? 'target' : 'target target--off'}>
      <legend className="visually-hidden">{metric.label}</legend>
      <div className="target__head">
        <label className="target__toggle">
          <input type="checkbox" checked={choice.enabled} onChange={(e) => set({ enabled: e.target.checked })} />
          <span className="target__name">{metric.label}</span>
        </label>
        <output className="target__value" htmlFor={id}>
          {choice.enabled ? formatMetric(metric, choice.value) : 'Not used'}
        </output>
      </div>
      <p className="target__desc">{metric.description}</p>

      <div className="target__track">
        <input id={id} type="range" className="court-range" min={metric.min} max={metric.max} step={step}
          value={choice.value}
          aria-valuetext={formatMetric(metric, choice.value)}
          aria-label={`${metric.label} target`}
          onChange={(e) => set({ enabled: true, level: null, value: roundToStep(Number(e.target.value), step) })} />
      </div>
      <div className="target__ticks" aria-hidden="true">
        {LEVELS.map(({ level, label, percentile }) => (
          <span key={level} className="target__tick" title={label}
            style={{ left: `${positionOnScale(metric, metric.percentiles[percentile])}%` }} />
        ))}
      </div>
      <div className="target__scale" aria-hidden="true">
        <span>{formatMetric(metric, metric.min)}</span>
        <span>{formatMetric(metric, metric.max)}</span>
      </div>

      <div className="target__controls">
        <div className="segmented" role="group" aria-label={`Quick ${metric.label} targets`}>
          {LEVELS.map(({ level, label, percentile }) => (
            <button key={level} type="button" aria-pressed={choice.enabled && choice.level === level}
              onClick={() => set({ enabled: true, level, value: metric.percentiles[percentile] })}>
              {label}
            </button>
          ))}
        </div>
        <div className="importance" role="radiogroup" aria-label={`How much ${metric.label} matters`}>
          <span className="importance__label">Matters</span>
          {IMPORTANCE.map((n) => (
            <label key={n} className={n <= choice.importance ? 'pip pip--on' : 'pip'}>
              <input type="radio" name={`${id}-importance`} value={n} checked={choice.importance === n}
                disabled={!choice.enabled} onChange={() => set({ importance: n })} />
              <span className="visually-hidden">{n} of 5</span>
            </label>
          ))}
        </div>
      </div>
    </fieldset>
  )
}
