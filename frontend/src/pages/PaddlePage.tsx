import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { BuyLink } from '../components/BuyLink'
import { CompareToggle } from '../components/CompareToggle'
import { Rail } from '../components/Rail'
import { Empty, ErrorNotice, Loading } from '../components/Status'
import { formatMetric, formatNumber, formatPrice, ordinal } from '../lib/format'
import { useReference } from '../lib/reference'
import { useApi } from '../lib/useApi'

export function PaddlePage() {
  const id = Number(useParams().id)
  const { metrics } = useReference()
  const detail = useApi(() => api.paddle(id), `paddle-${id}`)
  const similar = useApi(() => api.similar(id, 6), `similar-${id}`)

  if (detail.error) {
    return detail.error.message.startsWith('no paddle')
      ? <Empty title="That paddle isn't in the database."><Link to="/paddles">Browse all paddles</Link></Empty>
      : <ErrorNotice error={detail.error} />
  }
  if (!detail.data) return <Loading label="Loading paddle" />

  const { paddle, percentiles } = detail.data
  const playMetrics = metrics.filter((m) => m.key !== 'price')
  const facts: [string, string][] = [
    ['Type', paddle.paddle_type], ['Shape', paddle.shape], ['Impact feel', paddle.feel || '–'],
    ['Approval', paddle.approval], ['Released', paddle.year ? String(paddle.year) : '–'],
    ['Face', paddle.face || '–'], ['Grit', paddle.grit || '–'], ['Build', paddle.build || '–'],
    ['Spin rating', paddle.spin_rating || '–'], ['Spin durability', paddle.spin_durability || '–'],
  ]

  return (
    <article className="paddle">
      <Link to="/paddles" className="back">Back to all paddles</Link>
      <header className="paddle__head">
        <p className="paddle__brand">{paddle.brand}</p>
        <h1 className="display">{paddle.name}</h1>
        <p className="paddle__price">{formatPrice(paddle.price)}</p>
        <div className="paddle__actions">
          <CompareToggle id={paddle.id} name={paddle.full_name} />
          <BuyLink paddle={paddle} />
        </div>
      </header>

      <section aria-labelledby="sits-heading">
        <h2 id="sits-heading" className="section-title">Where it sits among all 494 paddles</h2>
        <p className="hint">The ball marks this paddle's percentile. Ticks mark the 20th, 50th and 80th.</p>
        <dl className="measure-list">
          {playMetrics.map((metric) => {
            const value = paddle[metric.key]
            const pct = percentiles[metric.key]
            return (
              <div key={metric.key} className="measure">
                <dt className="measure__label">
                  {metric.label}
                  <span className="measure__desc">{metric.description}</span>
                </dt>
                <dd className="measure__value">{formatMetric(metric, value)}</dd>
                <dd className="measure__rail">
                  {pct === undefined
                    ? <span className="muted">Not measured</span>
                    : <Rail marks={[{ position: pct, title: `${metric.label}: ${ordinal(pct)} percentile` }]} />}
                </dd>
                <dd className="measure__pct">{pct === undefined ? '' : ordinal(pct)}</dd>
              </div>
            )
          })}
        </dl>
      </section>

      <section aria-labelledby="facts-heading">
        <h2 id="facts-heading" className="section-title">Build</h2>
        <dl className="facts">
          {facts.map(([label, value]) => (
            <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
          ))}
        </dl>
      </section>

      <section aria-labelledby="similar-heading">
        <h2 id="similar-heading" className="section-title">Plays like</h2>
        <p className="hint">Paddles whose weight, swing weight, twist weight, balance, power, pop, spin and core are closest to this one.</p>
        {similar.error && <ErrorNotice error={similar.error} />}
        {!similar.data && !similar.error && <Loading label="Finding similar paddles" />}
        {similar.data && (
          <ol className="similar">
            {similar.data.map((item) => (
              <li key={item.paddle.id}>
                <Link to={`/paddles/${item.paddle.id}`} className="similar__name">{item.paddle.full_name}</Link>
                <span className="similar__meta">
                  {item.paddle.paddle_type}, {formatPrice(item.paddle.price)}, {formatNumber(item.paddle.swing_weight)} swing wt
                </span>
                <span className="similar__score">{item.score.toFixed(0)}% alike</span>
              </li>
            ))}
          </ol>
        )}
      </section>
    </article>
  )
}
