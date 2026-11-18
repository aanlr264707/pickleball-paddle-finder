import { Link } from 'react-router-dom'
import { Empty } from '../components/Status'

export function NotFoundPage() {
  return (
    <Empty title="That page is out of bounds.">
      <p><Link to="/">Back to the paddle finder</Link></p>
    </Empty>
  )
}
