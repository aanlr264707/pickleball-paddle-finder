import type { Paddle } from '../api/types'

export function BuyLink({ paddle }: { paddle: Paddle }) {
  if (!paddle.link) return null
  return (
    <a className="button button--quiet buy" href={paddle.link} target="_blank" rel="noopener noreferrer">
      Shop this paddle
    </a>
  )
}
