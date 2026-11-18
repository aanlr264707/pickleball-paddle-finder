import { Link } from 'react-router-dom'
import type { MetricKey, ScoredPaddle } from '../api/types'
import { formatMetric, formatPrice } from '../lib/format'
import { useReference } from '../lib/reference'
import { BuyLink } from './BuyLink'
import { CompareToggle } from './CompareToggle'

/** One ranked recommendation: rank, name, Match %, and how close each target came. */
export function ResultRow({ item, ranked }: { item: ScoredPaddle; ranked: boolean }) {
  const { metricsByKey } = useReference()
  const { paddle } = item
  const label = (key: MetricKey) => metricsByKey[key]?.label ?? key

  return (
    <li className="result">
      <span className="result__rank" aria-label={`Rank ${item.rank}`}>{item.rank}</span>
      <div className="result__main">
        <h3 className="result__name"><Link to={`/paddles/${paddle.id}`}>{paddle.name}</Link></h3>
        <p className="result__meta">
          <span className="result__brand">{paddle.brand}</span>
          <span>{paddle.paddle_type}</span>
          <span>{paddle.shape}</span>
          <span>{formatPrice(paddle.price)}</span>
          {!paddle.tournament_legal && <span className="flag">Not USAP approved</span>}
        </p>
        {item.fits.length > 0 && (
          <ul className="fits" aria-label="How close each target came">
            {item.fits.map((fit) => (
              <li key={fit.metric} className={fit.metric === item.worst_fit && item.fits.length > 1 ? 'fit fit--weak' : 'fit'}>
                <span className="fit__label">{label(fit.metric)}</span>
                <span className="fit__bar" aria-hidden="true">
                  <span style={{ width: `${Math.round(fit.similarity * 100)}%` }} />
                </span>
                <span className="fit__value">{formatMetric(metricsByKey[fit.metric], fit.value)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      {ranked && (
        <p className="result__score">
          <span className="score">{item.score.toFixed(1)}</span>
          <span className="score__label">% match</span>
        </p>
      )}
      <div className="result__actions">
        <CompareToggle id={paddle.id} name={paddle.full_name} />
        <BuyLink paddle={paddle} />
      </div>
    </li>
  )
}
