import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart,
  Tooltip, XAxis, YAxis, ZAxis,
} from 'recharts'
import { api } from '../api/client'
import type { Insights } from '../api/types'
import { Rail } from '../components/Rail'
import { ErrorNotice, Loading } from '../components/Status'
import { formatNumber, formatPrice, paddleFamily, type Family } from '../lib/format'
import { useApi } from '../lib/useApi'

// Validated categorical palette (dataviz skill: first three slots pass all-pairs CVD checks).
const FAMILY_COLORS: Record<Family, string> = { Control: '#2a78d6', 'All-Court': '#1baf7a', Power: '#eb6834' }
const FAMILIES: Family[] = ['Control', 'All-Court', 'Power']
const POSITIVE = '#2a78d6'
const NEGATIVE = '#eb6834'
const INK = '#13263D'
const INK_2 = '#4A5D72'
const GRID = '#DCE4EC'
const AXIS = { fontSize: 12, fill: INK_2 }

function ChartBlock({ title, note, table, children }: {
  title: string
  note: string
  table: { headers: string[]; rows: (string | number)[][] }
  children: ReactNode
}) {
  return (
    <figure className="chart">
      <figcaption>
        <h2 className="section-title">{title}</h2>
        <p className="hint">{note}</p>
      </figcaption>
      {children}
      <details className="chart__table">
        <summary>View as a table</summary>
        <table className="table table--small">
          <thead><tr>{table.headers.map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
          <tbody>{table.rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>)}</tbody>
        </table>
      </details>
    </figure>
  )
}

/** Dot plot: one court line per paddle type with a ball at the average (no zero baseline needed). */
function TypeDots({ rows, field, unit }: { rows: Insights['by_type']; field: string; unit: string }) {
  const values = rows.map((r) => Number(r[field]))
  const low = Math.floor(Math.min(...values))
  const high = Math.ceil(Math.max(...values))
  const position = (v: number) => (high === low ? 50 : ((v - low) / (high - low)) * 100)
  return (
    <div className="dots">
      {rows.map((row) => {
        const value = Number(row[field])
        return (
          <div key={row.paddle_type} className="dots__row">
            <span className="dots__label">{row.paddle_type}</span>
            <Rail compact ticks={[]} marks={[{ position: position(value), title: `${row.paddle_type}: ${formatNumber(value, 1)} ${unit}` }]} />
            <span className="dots__value">{formatNumber(value, 1)}</span>
          </div>
        )
      })}
      <div className="dots__row" aria-hidden="true">
        <span />
        <span className="dots__axis"><span>{low}{unit && ` ${unit}`}</span><span>{high}{unit && ` ${unit}`}</span></span>
        <span />
      </div>
    </div>
  )
}

interface ScatterPoint { id: number; brand: string; name: string; price: number; power: number; paddle_type: string }

function PointTooltip({ active, payload }: { active?: boolean; payload?: { payload: ScatterPoint }[] }) {
  if (!active || !payload?.length) return null
  const point = payload[0].payload
  return (
    <div className="tooltip">
      <strong>{point.brand} {point.name}</strong>
      <span>{point.paddle_type}</span>
      <span>{formatPrice(point.price)}, {formatNumber(point.power, 1)} MPH</span>
    </div>
  )
}

export function InsightsPage() {
  const { data, error } = useApi(api.insights, 'insights')
  const navigate = useNavigate()
  if (error) return <ErrorNotice error={error} />
  if (!data) return <Loading label="Crunching the numbers" />

  const { summary } = data
  const points = data.price_vs_power as ScatterPoint[]
  const first = data.by_type[0]
  const last = data.by_type[data.by_type.length - 1]
  const powerGap = Number(last.avg_power) - Number(first.avg_power)
  const strongest = Math.max(...data.power_drivers.map((d) => Math.abs(d.correlation)))
  const priceR = data.power_drivers.find((d) => d.metric === 'price')?.correlation ?? 0
  const powers = points.map((p) => p.power)
  const powerDomain: [number, number] = [Math.floor(Math.min(...powers)), Math.ceil(Math.max(...powers))]
  const priceDomain: [number, number] = [0, Math.ceil(Math.max(...points.map((p) => p.price)) / 50) * 50]
  const priceTicks = Array.from({ length: priceDomain[1] / 50 + 1 }, (_, i) => i * 50)

  return (
    <>
      <section className="intro intro--tight">
        <h1 className="display display--small">What the measurements say</h1>
        <p className="lede">
          {summary.paddles} paddles from {summary.brands} brands. The median paddle costs{' '}
          {formatPrice(summary.median_price)}, and {Math.round(summary.usap_share * 100)}% are approved for
          USA Pickleball tournaments.
        </p>
      </section>

      <div className="chart-grid">
        <ChartBlock title="Power paddles really do hit harder"
          note={`Average ball speed by paddle type, from most control to most power. ${last.paddle_type} paddles average ${powerGap.toFixed(1)} MPH more on full swings than ${first.paddle_type} paddles, and pop rises with them.`}
          table={{ headers: ['Type', 'Paddles', 'Avg power (MPH)', 'Avg pop (MPH)', 'Avg price'],
            rows: data.by_type.map((r) => [r.paddle_type, r.count, formatNumber(Number(r.avg_power), 1),
              formatNumber(Number(r.avg_pop), 1), formatPrice(Number(r.avg_price))]) }}>
          <div className="dots-pair">
            <div><h3 className="dots__title">Power, full swings (MPH)</h3><TypeDots rows={data.by_type} field="avg_power" unit="" /></div>
            <div><h3 className="dots__title">Pop, short swings (MPH)</h3><TypeDots rows={data.by_type} field="avg_pop" unit="" /></div>
          </div>
        </ChartBlock>

        <ChartBlock title="No single spec predicts power"
          note={`Correlation of each build measurement with full-swing power, from −1 to 1. None is stronger than ${strongest.toFixed(2)}, so a spec sheet alone won't tell you how hard a paddle hits. That's why the power test matters.`}
          table={{ headers: ['Measurement', 'Correlation with power'],
            rows: data.power_drivers.map((d) => [d.label, d.correlation.toFixed(2)]) }}>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.power_drivers} layout="vertical" margin={{ top: 4, right: 40, bottom: 4, left: 8 }}
              barCategoryGap={2}>
              <CartesianGrid horizontal={false} stroke={GRID} />
              <XAxis type="number" domain={[-1, 1]} ticks={[-1, -0.5, 0, 0.5, 1]} tick={AXIS} stroke={GRID} />
              <YAxis type="category" dataKey="label" width={96} tick={{ ...AXIS, fill: INK }} stroke={GRID} />
              <ReferenceLine x={0} stroke={INK_2} />
              <Tooltip cursor={{ fill: 'rgba(43,93,140,0.06)' }}
                formatter={(value) => [Number(value).toFixed(2), 'Correlation']} />
              <Bar dataKey="correlation" radius={2} maxBarSize={18} isAnimationActive={false}
                label={{ position: 'right', fill: INK_2, fontSize: 12, formatter: (v: unknown) => Number(v).toFixed(2) }}>
                {data.power_drivers.map((d) => <Cell key={d.metric} fill={d.correlation >= 0 ? POSITIVE : NEGATIVE} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartBlock>

        <ChartBlock title="Price doesn't buy power"
          note={`Every paddle with a price and a power measurement (correlation ${priceR.toFixed(2)}). Select a dot to open that paddle.`}
          table={{ headers: ['Paddle', 'Type', 'Price', 'Power (MPH)'],
            rows: points.map((p) => [`${p.brand} ${p.name}`, p.paddle_type, formatPrice(p.price), formatNumber(p.power, 1)]) }}>
          <ul className="legend" aria-label="Paddle families">
            {FAMILIES.map((family) => (
              <li key={family}><span className="legend__swatch" style={{ background: FAMILY_COLORS[family] }} />{family}</li>
            ))}
          </ul>
          <ResponsiveContainer width="100%" height={340}>
            <ScatterChart margin={{ top: 8, right: 16, bottom: 24, left: 4 }}>
              <CartesianGrid stroke={GRID} />
              <XAxis type="number" dataKey="price" name="Price" tick={AXIS} stroke={GRID}
                domain={priceDomain} ticks={priceTicks} tickFormatter={(v) => `$${Math.round(v)}`}
                label={{ value: 'Price', position: 'insideBottom', offset: -14, fill: INK_2, fontSize: 12 }} />
              <YAxis type="number" dataKey="power" name="Power" tick={AXIS} stroke={GRID}
                domain={powerDomain} allowDecimals={false} tickCount={powerDomain[1] - powerDomain[0] + 1}
                label={{ value: 'Power (MPH)', angle: -90, position: 'insideLeft', fill: INK_2, fontSize: 12, dy: 40 }} />
              <ZAxis range={[64, 64]} />
              <Tooltip content={<PointTooltip />} cursor={{ strokeDasharray: '3 3', stroke: INK_2 }} />
              {FAMILIES.map((family) => (
                <Scatter key={family} name={family} fill={FAMILY_COLORS[family]} stroke="#ffffff" strokeWidth={1.5}
                  fillOpacity={0.9} cursor="pointer" isAnimationActive={false}
                  data={points.filter((p) => paddleFamily(p.paddle_type) === family)}
                  onClick={(point) => {
                    const id = (point as unknown as { payload?: ScatterPoint }).payload?.id ?? (point as unknown as ScatterPoint).id
                    if (id) navigate(`/paddles/${id}`)
                  }} />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </ChartBlock>

        <ChartBlock title="Brands with the most paddles tested"
          note={`The ${data.top_brands.length} brands with the most paddles in the database.`}
          table={{ headers: ['Brand', 'Paddles'], rows: data.top_brands.map((b) => [b.value, b.count]) }}>
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={data.top_brands} layout="vertical" margin={{ top: 4, right: 32, bottom: 4, left: 8 }}
              barCategoryGap={2}>
              <CartesianGrid horizontal={false} stroke={GRID} />
              <XAxis type="number" tick={AXIS} stroke={GRID} allowDecimals={false} />
              <YAxis type="category" dataKey="value" width={110} tick={{ ...AXIS, fill: INK }} stroke={GRID} />
              <Tooltip cursor={{ fill: 'rgba(43,93,140,0.06)' }} formatter={(value) => [value, 'Paddles']} />
              <Bar dataKey="count" fill="#2B5D8C" radius={[0, 4, 4, 0]} maxBarSize={18} isAnimationActive={false}
                label={{ position: 'right', fill: INK_2, fontSize: 12 }} />
            </BarChart>
          </ResponsiveContainer>
        </ChartBlock>
      </div>
    </>
  )
}
