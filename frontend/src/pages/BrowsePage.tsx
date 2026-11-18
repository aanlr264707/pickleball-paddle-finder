import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import type { MetricKey } from '../api/types'
import { CompareToggle } from '../components/CompareToggle'
import { Empty, ErrorNotice, Loading } from '../components/Status'
import { formatMetric, formatPrice } from '../lib/format'
import { useReference } from '../lib/reference'
import { useApi } from '../lib/useApi'

const COLUMNS: { key: 'name' | MetricKey; label: string; numeric: boolean }[] = [
  { key: 'name', label: 'Paddle', numeric: false },
  { key: 'price', label: 'Price', numeric: true },
  { key: 'weight', label: 'Weight', numeric: true },
  { key: 'swing_weight', label: 'Swing wt', numeric: true },
  { key: 'twist_weight', label: 'Twist wt', numeric: true },
  { key: 'power', label: 'Power', numeric: true },
  { key: 'pop', label: 'Pop', numeric: true },
  { key: 'spin', label: 'Spin', numeric: true },
]
const PER_PAGE = 25

export function BrowsePage() {
  const { options, metricsByKey } = useReference()
  const [params, setParams] = useSearchParams()
  const [text, setText] = useState(params.get('q') ?? '')

  const query = {
    q: params.get('q') ?? '',
    brand: params.get('brand') ?? '',
    paddle_type: params.get('paddle_type') ?? '',
    shape: params.get('shape') ?? '',
    tournament_only: params.get('tournament_only') === 'true',
    sort: params.get('sort') ?? 'name',
    order: params.get('order') ?? 'asc',
    page: Number(params.get('page') ?? 1) || 1,
    per_page: PER_PAGE,
  }
  const { data, error, loading } = useApi(() => api.paddles(query), params.toString())

  const update = (patch: Record<string, string | null>, resetPage = true) => {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(patch)) {
      if (value) next.set(key, value)
      else next.delete(key)
    }
    if (resetPage) next.delete('page')
    setParams(next, { replace: true })
  }

  // Search as you type, a beat after the last keystroke.
  useEffect(() => {
    const timer = setTimeout(() => {
      if (text.trim() !== query.q) update({ q: text.trim() || null })
    }, 250)
    return () => clearTimeout(timer)
  }, [text]) // re-run only when the typed text changes

  const sortBy = (key: string) => {
    const order = query.sort === key && query.order === 'asc' ? 'desc' : 'asc'
    update({ sort: key, order })
  }
  const ariaSort = (key: string) =>
    query.sort === key ? (query.order === 'asc' ? 'ascending' : 'descending') : 'none'

  return (
    <>
      <section className="intro intro--tight">
        <h1 className="display display--small">Browse every paddle</h1>
        <p className="lede">Search by name, narrow the list, and sort by any measurement. Missing measurements sort last.</p>
      </section>

      <form className="toolbar" role="search" onSubmit={(e) => e.preventDefault()}>
        <div className="field field--grow">
          <label htmlFor="search">Search</label>
          <input id="search" type="search" placeholder="Brand or model, e.g. joola perseus" value={text}
            onChange={(e) => setText(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="brand">Brand</label>
          <select id="brand" value={query.brand} onChange={(e) => update({ brand: e.target.value })}>
            <option value="">All brands</option>
            {options.brand.map((b) => <option key={b}>{b}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="type">Type</label>
          <select id="type" value={query.paddle_type} onChange={(e) => update({ paddle_type: e.target.value })}>
            <option value="">All types</option>
            {options.paddle_type.map((t) => <option key={t}>{t}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="shape">Shape</label>
          <select id="shape" value={query.shape} onChange={(e) => update({ shape: e.target.value })}>
            <option value="">All shapes</option>
            {options.shape.map((s) => <option key={s}>{s}</option>)}
          </select>
        </div>
        <label className="check check--toolbar">
          <input type="checkbox" checked={query.tournament_only}
            onChange={(e) => update({ tournament_only: e.target.checked ? 'true' : null })} />
          USAP approved
        </label>
      </form>

      {error && <ErrorNotice error={error} />}
      {!data && loading && <Loading label="Loading paddles" />}
      {data && data.total === 0 && (
        <Empty title="No paddles match.">
          <p>Try fewer words, or set brand, type and shape back to All.</p>
        </Empty>
      )}
      {data && data.total > 0 && (
        <>
          <p className="table-caption" aria-live="polite">
            {data.total} paddle{data.total === 1 ? '' : 's'}
            {loading && <span className="status-inline"> updating…</span>}
          </p>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  {COLUMNS.map((col) => (
                    <th key={col.key} scope="col" aria-sort={ariaSort(col.key)} className={col.numeric ? 'num' : undefined}>
                      <button type="button" className="sort" onClick={() => sortBy(col.key)}>
                        {col.label}
                        <span className="sort__mark" aria-hidden="true">
                          {query.sort === col.key ? (query.order === 'asc' ? '▲' : '▼') : ''}
                        </span>
                      </button>
                    </th>
                  ))}
                  <th scope="col"><span className="visually-hidden">Compare</span></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((paddle) => (
                  <tr key={paddle.id}>
                    <th scope="row">
                      <Link to={`/paddles/${paddle.id}`} className="table__name">{paddle.name}</Link>
                      <span className="table__sub">{paddle.brand}, {paddle.paddle_type}, {paddle.shape}</span>
                    </th>
                    <td className="num">{formatPrice(paddle.price)}</td>
                    {COLUMNS.slice(2).map((col) => (
                      <td key={col.key} className="num">
                        {formatMetric(metricsByKey[col.key as MetricKey], paddle[col.key as MetricKey])}
                      </td>
                    ))}
                    <td><CompareToggle id={paddle.id} name={paddle.full_name} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <nav className="pager" aria-label="Pages">
            <button type="button" className="button button--quiet" disabled={data.page <= 1}
              onClick={() => update({ page: String(data.page - 1) }, false)}>Previous</button>
            <span>Page {data.page} of {data.pages}</span>
            <button type="button" className="button button--quiet" disabled={data.page >= data.pages}
              onClick={() => update({ page: String(data.page + 1) }, false)}>Next</button>
          </nav>
        </>
      )}
    </>
  )
}
