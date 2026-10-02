import { useCallback, useMemo, useState } from 'react'
import Badge from '../Badge.jsx'
import StreamMap from '../StreamMap.jsx'
import { LEVELS, LEVEL_ORDER, longDate, mainReason } from '../lib.js'

export default function Home({ data }) {
  const { counts, streams } = data
  const [city, setCity] = useState('All')
  const [level, setLevel] = useState('all')
  const cities = useMemo(() => ['All', ...new Set(streams.map((s) => s.city))].sort((a, b) =>
    a === 'All' ? -1 : b === 'All' ? 1 : a.localeCompare(b)), [streams])

  const inCity = useMemo(() => streams.filter((s) => city === 'All' || s.city === city), [streams, city])
  const shown = useMemo(() => inCity.filter((s) => level === 'all' || s.level === level), [inCity, level])
  const open = useCallback((s) => { window.location.hash = `/stream/${s.code}` }, [])

  return (
    <>
      <section className="hero">
        <h1>Which streams are overdue for a check-up?</h1>
        <p className="lead">
          OneAquaHealth watches {counts.streams} city streams in {counts.cities} European cities.{' '}
          <strong>{counts.labFrom2023} of the {counts.withLab} lab results are from 2023</strong>, and each stream
          was sampled once. This page shows where to look first, and why.
        </p>
        <div className="tiles">
          <div className="tile"><b>{counts.labFrom2023} of {counts.withLab}</b><span>lab results are three years old</span></div>
          <div className="tile"><b>{counts.never}</b><span>streams have never been checked</span></div>
          <div className="tile"><b>{counts.first}</b><span>streams to check first</span></div>
          <a className="tile link" href="#/records"><b>{counts.recordProblems}</b><span>records that cannot be right →</span></a>
        </div>
        <div className="changes">
          <strong>
            {data.changes.sinceIsFirst ? 'Since the first check' : 'Since the last check'} on {longDate(data.changes.since)}:
          </strong>{' '}
          {data.changes.items.length === 0
            ? 'nothing has changed in OneAquaHealth\'s data.'
            : <ul>{data.changes.items.map((item) => <li key={item}>{item}</li>)}</ul>}
        </div>
      </section>

      <section aria-label="Streams">
        <div className="filters">
          <div className="chips" role="group" aria-label="City">
            {cities.map((c) => (
              <button key={c} className="chip" aria-pressed={city === c} onClick={() => setCity(c)}>{c}</button>
            ))}
            {city !== 'All' && <a className="brieflink" href={`#/brief/${city}`}>Print the {city} brief →</a>}
          </div>
          <div className="chips" role="group" aria-label="Level">
            <button className="chip" aria-pressed={level === 'all'} onClick={() => setLevel('all')}>
              All levels <i>{inCity.length}</i>
            </button>
            {LEVEL_ORDER.map((k) => (
              <button key={k} className="chip" aria-pressed={level === k} onClick={() => setLevel(k)}
                style={{ '--c': LEVELS[k].color }}>
                <span className="dot" aria-hidden="true" />
                {LEVELS[k].label} <i>{inCity.filter((s) => s.level === k).length}</i>
              </button>
            ))}
          </div>
        </div>

        <div className="split">
          <StreamMap streams={shown} onPick={open} />
          <ol className="list" aria-label="Streams in order of priority">
            {shown.length === 0 && <li className="empty">No streams at this level in {city}.</li>}
            {shown.map((s) => (
              <li key={s.code}>
                <a href={`#/stream/${s.code}`}>
                  <div className="row">
                    <strong>{s.name}</strong>
                    <Badge level={s.level} />
                  </div>
                  <span className="where">{s.city} · {s.code}</span>
                  <span className="why">{mainReason(s)}</span>
                </a>
              </li>
            ))}
          </ol>
        </div>
      </section>
    </>
  )
}
