import { NavLink, Outlet } from 'react-router-dom'
import { useCompare } from '../lib/compare'

const LINKS = [
  { to: '/', label: 'Find', end: true },
  { to: '/paddles', label: 'Browse', end: false },
  { to: '/insights', label: 'Insights', end: false },
]

export function Layout() {
  const { ids } = useCompare()
  return (
    <>
      <a className="skip-link" href="#main">Skip to content</a>
      <header className="site-header">
        <div className="site-header__inner">
          <NavLink to="/" className="wordmark" aria-label="Paddle Finder home">
            <span className="wordmark__ball" aria-hidden="true" />
            Paddle Finder
          </NavLink>
          <nav aria-label="Main">
            <ul className="nav">
              {LINKS.map((link) => (
                <li key={link.to}>
                  <NavLink to={link.to} end={link.end} className="nav__link">{link.label}</NavLink>
                </li>
              ))}
              <li>
                <NavLink to="/compare" className="nav__link">
                  Compare{ids.length > 0 && <span className="nav__count" aria-label={`${ids.length} picked`}>{ids.length}</span>}
                </NavLink>
              </li>
            </ul>
          </nav>
        </div>
      </header>
      <main id="main" className="page">
        <Outlet />
      </main>
      <footer className="site-footer">
        <p>
          Measurements from the Pickleball Effect paddle database. Built with Flask, PostgreSQL,
          pandas and React.
        </p>
      </footer>
    </>
  )
}
