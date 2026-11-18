import { useCompare } from '../lib/compare'

export function CompareToggle({ id, name }: { id: number; name: string }) {
  const { has, toggle, full } = useCompare()
  const picked = has(id)
  return (
    <button type="button" className={picked ? 'chip chip--on' : 'chip'} aria-pressed={picked}
      disabled={!picked && full} onClick={() => toggle(id)}
      title={!picked && full ? 'Compare holds four paddles. Remove one first.' : undefined}
      aria-label={`${picked ? 'Remove' : 'Add'} ${name} ${picked ? 'from' : 'to'} compare`}>
      {picked ? 'In compare' : 'Compare'}
    </button>
  )
}
