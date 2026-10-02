import { longDate, useData, useRoute } from './lib.js'
import Home from './pages/Home.jsx'
import Stream from './pages/Stream.jsx'
import Records from './pages/Records.jsx'
import Near from './pages/Near.jsx'
import How from './pages/How.jsx'
import Requests from './pages/Requests.jsx'
import Brief from './pages/Brief.jsx'

const NAV = [
  ['/', 'Streams'],
  ['/requests', 'Visit requests'],
  ['/records', 'Record problems'],
  ['/near', 'Near me'],
  ['/how', 'How it works'],
]

export default function App() {
  const { data, error } = useData()
  const route = useRoute()

  let page
  if (error) page = <p className="notice">The data could not be loaded. {String(error.message)}</p>
  else if (!data) page = <p className="notice">Loading the streams…</p>
  else if (route.startsWith('/stream/')) page = <Stream data={data} code={decodeURIComponent(route.slice(8))} />
  else if (route === '/records') page = <Records data={data} />
  else if (route === '/requests') page = <Requests />
  else if (route.startsWith('/brief/')) page = <Brief data={data} city={decodeURIComponent(route.slice(7))} />
  else if (route === '/near') page = <Near data={data} />
  else if (route === '/how') page = <How data={data} />
  else page = <Home data={data} />

  const current = route.startsWith('/stream/') || route.startsWith('/brief/') ? '/' : route
  return (
    <>
      <header className="top noprint">
        <a className="brand" href="#/">
          <svg viewBox="0 0 32 32" width="26" height="26" aria-hidden="true">
            <path d="M16 3C11 11 7 15 7 20a9 9 0 0 0 18 0c0-5-4-9-9-17z" fill="currentColor" />
          </svg>
          Stream Check-up
        </a>
        <nav aria-label="Main">
          {NAV.map(([to, label]) => (
            <a key={to} href={`#${to}`} aria-current={current === to ? 'page' : undefined}>{label}</a>
          ))}
        </nav>
      </header>
      <main>{page}</main>
      <footer className="foot noprint">
        {data && (
          <p>
            Built on OneAquaHealth's own public data, copied on {longDate(data.snapshot)}. Weather on record up
            to {longDate(data.lastWeatherDay)}.
          </p>
        )}
        <p>
          A community prototype for the OneAquaHealth IEEE Global Hackathon 2026. Not an official OneAquaHealth
          product. Map © OpenStreetMap contributors.
        </p>
      </footer>
    </>
  )
}
