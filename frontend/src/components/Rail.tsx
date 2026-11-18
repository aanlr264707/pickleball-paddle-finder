export interface RailMark {
  /** Position from 0 to 100. */
  position: number
  /** Short text inside the ball (compare view: A, B, C...). */
  label?: string
  /** Accessible description, e.g. "JOOLA Perseus: 81st percentile". */
  title: string
  /** Lane index when the rail is split into lanes (one per paddle). */
  lane?: number
}

/**
 * The signature graphic: a court line with a ball on it.
 * With `lanes`, each paddle gets its own line so equal values never hide each other.
 * Read-only; the questionnaire's interactive version is TargetRail.
 */
export function Rail({ marks, ticks = [20, 50, 80], compact = false, lanes = 0 }: {
  marks: RailMark[]
  ticks?: number[]
  compact?: boolean
  lanes?: number
}) {
  const classes = ['rail', compact && 'rail--compact', lanes > 1 && 'rail--lanes'].filter(Boolean).join(' ')
  const laneTop = (lane: number) => `${((lane + 0.5) / lanes) * 100}%`
  return (
    <div className={classes} role="img" aria-label={marks.map((mark) => mark.title).join('; ')}
      style={lanes > 1 ? { height: `${lanes * 18 + 4}px` } : undefined}>
      {lanes > 1 && Array.from({ length: lanes }, (_, lane) => (
        <span key={lane} className="rail__lane" style={{ top: laneTop(lane) }} />
      ))}
      <span className="rail__field">
        {ticks.map((tick) => <span key={tick} className="rail__tick" style={{ left: `${tick}%` }} />)}
        {marks.map((mark, index) => (
          <span key={index} className={mark.label ? 'ball ball--labelled' : 'ball'} title={mark.title}
            style={{ left: `${mark.position}%`, ...(lanes > 1 && mark.lane !== undefined ? { top: laneTop(mark.lane) } : {}) }}>
            {mark.label}
          </span>
        ))}
      </span>
    </div>
  )
}
