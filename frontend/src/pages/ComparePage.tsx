import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { Paddle } from '../api/types'
import { Rail } from '../components/Rail'
import { Empty, ErrorNotice, Loading } from '../components/Status'
import { MAX_COMPARE, useCompare } from '../lib/compare'
import { formatMetric, formatPrice, ordinal } from '../lib/format'
import { useReference } from '../lib/reference'
import { useApi } from '../lib/useApi'

const LETTERS = ['A', 'B', 'C', 'D']
const TEXT_ROWS: { key: keyof Paddle; label: string }[] = [
  { key: 'paddle_type', label: 'Type' }, { key: 'shape', label: 'Shape' }, { key: 'feel', label: 'Impact feel' },
  { key: 'approval', label: 'Approval' }, { key: 'face', label: 'Face' }, { key: 'spin_durability', label: 'Spin durability' },
]

function AddPaddle() {
  const { ids, toggle, full } = useCompare()
  const [text, setText] = useState('')
  const term = text.trim()
  const found = useApi(() => (term.length < 2 ? Promise.resolve(null) : api.paddles({ q: term, per_page: 8 })), term)
  if (full) return <p className="hint">Compare holds {MAX_COMPARE} paddles. Remove one to add another.</p>
  return (
    <div className="add-paddle">
      <label htmlFor="add-paddle">Add a paddle</label>
      <input id="add-paddle" type="search" placeholder="Search by name" value={text} onChange={(e) => setText(e.target.value)} />
      {found.data && (
        <ul className="add-paddle__list">
          {found.data.items.filter((p) => !ids.includes(p.id)).map((p) => (
            <li key={p.id}>
              <button type="button" onClick={() => { toggle(p.id); setText('') }}>{p.full_name}</button>
            </li>
          ))}
          {found.data.total === 0 && <li className="muted">No paddle matches “{term}”.</li>}
        </ul>
      )}
    </div>
  )
}

export function ComparePage() {
  const { ids, remove, clear } = useCompare()
  const { metrics } = useReference()
  const data = useApi(() => (ids.length >= 2 ? api.compare(ids) : Promise.resolve([])), ids.join(','))

  return (
    <>
      <section className="intro intro--tight">
        <h1 className="display display--small">Compare side by side</h1>
        <p className="lede">Up to four paddles. Each line shows where every paddle sits from the lowest to the highest measured.</p>
      </section>
      <AddPaddle />

      {ids.length < 2 && (
        <Empty title={ids.length === 0 ? 'Nothing to compare yet.' : 'Pick one more paddle.'}>
          <p>Use Compare on any paddle in <Link to="/paddles">Browse</Link> or in your results, or search above.</p>
        </Empty>
      )}
      {ids.length >= 2 && data.error && <ErrorNotice error={data.error} />}
      {ids.length >= 2 && !data.data && !data.error && <Loading label="Loading comparison" />}
      {ids.length >= 2 && data.data && data.data.length >= 2 && (
        <>
          <div className="table-wrap">
            <table className="compare">
              <thead>
                <tr>
                  <td />
                  {data.data.map(({ paddle }, index) => (
                    <th key={paddle.id} scope="col">
                      <span className="compare__letter" aria-hidden="true">{LETTERS[index]}</span>
                      <Link to={`/paddles/${paddle.id}`} className="compare__name">{paddle.name}</Link>
                      <span className="compare__brand">{paddle.brand}, {formatPrice(paddle.price)}</span>
                      <button type="button" className="link-button" onClick={() => remove(paddle.id)}>Remove</button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {metrics.map((metric) => {
                  const values = data.data!.map(({ paddle }) => paddle[metric.key])
                  const known = values.filter((v): v is number => v !== null)
                  const top = known.length > 1 && new Set(known).size > 1 ? Math.max(...known) : null
                  return (
                    <tr key={metric.key}>
                      <th scope="row">
                        {metric.label}
                        <Rail compact ticks={[]} lanes={data.data!.length} marks={data.data!.flatMap(({ paddle, percentiles }, index) =>
                          percentiles[metric.key] === undefined ? [] : [{
                            position: percentiles[metric.key]!, label: LETTERS[index], lane: index,
                            title: `${paddle.full_name}: ${ordinal(percentiles[metric.key]!)} percentile`,
                          }])} />
                      </th>
                      {data.data!.map(({ paddle, percentiles }) => {
                        const value = paddle[metric.key]
                        return (
                          <td key={paddle.id} className={value !== null && value === top ? 'is-top' : undefined}>
                            <span className="compare__value">{formatMetric(metric, value)}</span>
                            {percentiles[metric.key] !== undefined && (
                              <span className="compare__pct">{ordinal(percentiles[metric.key]!)} pct</span>
                            )}
                          </td>
                        )
                      })}
                    </tr>
                  )
                })}
                {TEXT_ROWS.map((row) => (
                  <tr key={row.key}>
                    <th scope="row">{row.label}</th>
                    {data.data!.map(({ paddle }) => <td key={paddle.id}>{String(paddle[row.key] || '–')}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="hint compare-note">Bold marks the highest value in a row. Higher isn't always better: lighter swing weight means faster hands.</p>
          <button type="button" className="button button--quiet" onClick={clear}>Clear compare</button>
        </>
      )}
    </>
  )
}
