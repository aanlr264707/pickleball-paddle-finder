import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { BrowsePage } from './pages/BrowsePage'
import { ComparePage } from './pages/ComparePage'
import { FinderPage } from './pages/FinderPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { PaddlePage } from './pages/PaddlePage'
import { Loading } from './components/Status'

// Charts (recharts) are only downloaded when someone opens Insights.
const InsightsPage = lazy(() => import('./pages/InsightsPage').then((m) => ({ default: m.InsightsPage })))

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<FinderPage />} />
        <Route path="paddles" element={<BrowsePage />} />
        <Route path="paddles/:id" element={<PaddlePage />} />
        <Route path="compare" element={<ComparePage />} />
        <Route path="insights" element={<Suspense fallback={<Loading label="Loading charts" />}><InsightsPage /></Suspense>} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
