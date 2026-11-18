import { useRef, useState, type FormEvent } from 'react'
import { ApiError, api } from '../api/client'
import type { Filters, MetricKey, PreferenceInput, Preset, Recommendations } from '../api/types'
import { ResultRow } from '../components/ResultRow'
import { ErrorNotice } from '../components/Status'
import { defaultChoice, TargetRail, type MetricChoice } from '../components/TargetRail'
import { useReference } from '../lib/reference'

const EMPTY_FILTERS: Filters = { max_price: null, tournament_only: false, shape: null, paddle_type: null, feel: null }
const RESULT_COUNT = 10

export function FinderPage() {
  const { metrics, metricsByKey, options, presets } = useReference()
  const questionMetrics = metrics.filter((m) => m.in_questionnaire)
  const initialChoices = () =>
    Object.fromEntries(questionMetrics.map((m) => [m.key, defaultChoice(m)])) as Record<MetricKey, MetricChoice>

  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)
  const [budget, setBudget] = useState('')
  const [choices, setChoices] = useState(initialChoices)
  const [activePreset, setActivePreset] = useState<string | null>(null)
  const [result, setResult] = useState<Recommendations | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [busy, setBusy] = useState(false)
  const resultsRef = useRef<HTMLElement>(null)

  const setFilter = <K extends keyof Filters>(key: K, value: Filters[K]) =>
    setFilters((current) => ({ ...current, [key]: value }))

  const applyPreset = (preset: Preset) => {
    const next = initialChoices()
    for (const target of preset.targets) {
      const metric = metricsByKey[target.metric]
      const level = typeof target.target === 'string' ? target.target : null
      const percentile = { low: '20', medium: '50', high: '80' } as const
      next[target.metric] = {
        enabled: true,
        level,
        value: level ? metric.percentiles[percentile[level]] : (target.target as number),
        importance: target.importance,
      }
    }
    setChoices(next)
    setActivePreset(preset.slug)
  }

  const reset = () => {
    setFilters(EMPTY_FILTERS)
    setBudget('')
    setChoices(initialChoices())
    setActivePreset(null)
    setResult(null)
    setError(null)
  }

  const budgetValue = budget.trim() === '' ? null : Number(budget)
  const budgetInvalid = budgetValue !== null && (!Number.isFinite(budgetValue) || budgetValue < 0)
  const activeCount = Object.values(choices).filter((c) => c.enabled).length

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (budgetInvalid) return
    const preferences: PreferenceInput[] = questionMetrics
      .filter((m) => choices[m.key].enabled)
      .map((m) => ({ metric: m.key, target: choices[m.key].level ?? choices[m.key].value, importance: choices[m.key].importance }))
    setBusy(true)
    setError(null)
    try {
      const response = await api.recommend({ filters: { ...filters, max_price: budgetValue }, preferences, limit: RESULT_COUNT })
      setResult(response)
      requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught : new Error('Something went wrong ranking paddles.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <section className="intro">
        <h1 className="display">Find a paddle that plays like you do.</h1>
        <p className="lede">
          494 paddles, each measured in a lab for swing weight, power, spin and more. Set your must-haves,
          place the ball where you want each measurement, and every paddle gets a Match&nbsp;%.
        </p>
      </section>

      <section className="presets" aria-labelledby="presets-heading">
        <h2 id="presets-heading" className="section-title">Start from a play style</h2>
        <div className="preset-list">
          {presets.map((preset) => (
            <button key={preset.slug} type="button" className="preset" aria-pressed={activePreset === preset.slug}
              onClick={() => applyPreset(preset)}>
              <span className="preset__name">{preset.name}</span>
              <span className="preset__desc">{preset.description}</span>
            </button>
          ))}
        </div>
      </section>

      <form className="finder" onSubmit={submit} noValidate>
        <section className="finder__musts" aria-labelledby="musts-heading">
          <h2 id="musts-heading" className="section-title">Must-haves</h2>
          <div className="field">
            <label htmlFor="budget">Budget</label>
            <div className="input-prefix">
              <span aria-hidden="true">$</span>
              <input id="budget" inputMode="decimal" placeholder="No limit" value={budget}
                aria-invalid={budgetInvalid} aria-describedby={budgetInvalid ? 'budget-error' : undefined}
                onChange={(e) => setBudget(e.target.value)} />
            </div>
            {budgetInvalid && <p id="budget-error" className="field__error">Enter a dollar amount, like 200.</p>}
          </div>
          <label className="check">
            <input type="checkbox" checked={filters.tournament_only}
              onChange={(e) => setFilter('tournament_only', e.target.checked)} />
            Approved for USA Pickleball tournaments
          </label>
          <fieldset className="field">
            <legend>Shape</legend>
            <div className="segmented segmented--wrap">
              {[null, ...options.shape].map((shape) => (
                <button key={shape ?? 'any'} type="button" aria-pressed={filters.shape === shape}
                  onClick={() => setFilter('shape', shape)}>{shape ?? 'Any'}</button>
              ))}
            </div>
          </fieldset>
          <div className="field">
            <label htmlFor="paddle-type">Paddle type</label>
            <select id="paddle-type" value={filters.paddle_type ?? ''}
              onChange={(e) => setFilter('paddle_type', e.target.value || null)}>
              <option value="">Any type</option>
              {options.paddle_type.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="feel">Impact feel</label>
            <select id="feel" value={filters.feel ?? ''} onChange={(e) => setFilter('feel', e.target.value || null)}>
              <option value="">Any feel</option>
              {options.feel.map((f) => <option key={f}>{f}</option>)}
            </select>
          </div>
        </section>

        <section className="finder__targets" aria-labelledby="targets-heading">
          <h2 id="targets-heading" className="section-title">How it should play</h2>
          <p className="hint">
            Turn on the measurements you care about. Low, Medium and High are the 20th, 50th and 80th percentile
            of all paddles.
          </p>
          <div className="target-list">
            {questionMetrics.map((metric) => (
              <TargetRail key={metric.key} metric={metric} choice={choices[metric.key]}
                onChange={(choice) => { setChoices((c) => ({ ...c, [metric.key]: choice })); setActivePreset(null) }} />
            ))}
          </div>
        </section>

        <div className="finder__submit">
          <button type="submit" className="button button--primary" disabled={busy || budgetInvalid}>
            {busy ? 'Ranking…' : 'Rank paddles'}
          </button>
          <button type="button" className="button button--quiet" onClick={reset}>Start over</button>
          <span className="finder__count">
            {activeCount === 0 ? 'No targets yet: results will only be filtered.' : `${activeCount} target${activeCount === 1 ? '' : 's'} set`}
          </span>
        </div>
      </form>

      <section ref={resultsRef} className="results" aria-live="polite" aria-labelledby="results-heading">
        {error && <ErrorNotice error={error} />}
        {result && (
          <>
            <h2 id="results-heading" className="section-title">
              {result.results.length === 0 ? 'No paddles fit those must-haves' : `Your top ${result.results.length}`}
            </h2>
            <p className="hint">
              {result.results.length === 0
                ? 'Raise the budget or set shape, type or feel back to Any.'
                : `${result.candidates} paddles passed your must-haves. ${result.ranked ? 'Ranked by Match %.' : 'Set a target to rank them.'}`}
            </p>
            <ol className="result-list">
              {result.results.map((item) => <ResultRow key={item.paddle.id} item={item} ranked={result.ranked} />)}
            </ol>
          </>
        )}
      </section>
    </>
  )
}
