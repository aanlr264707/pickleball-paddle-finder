import '@fontsource-variable/archivo/wdth.css'
import './styles.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { App } from './App'
import { ErrorNotice, Loading } from './components/Status'
import { CompareProvider } from './lib/compare'
import { ReferenceProvider } from './lib/reference'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ReferenceProvider fallback={({ error }) => (
        <main className="page">{error ? <ErrorNotice error={error} /> : <Loading label="Loading paddle data" />}</main>
      )}>
        <CompareProvider>
          <App />
        </CompareProvider>
      </ReferenceProvider>
    </BrowserRouter>
  </StrictMode>,
)
