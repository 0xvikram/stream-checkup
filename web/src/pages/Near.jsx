import { useMemo, useState } from 'react'
import Badge from '../Badge.jsx'
import StreamMap from '../StreamMap.jsx'
import { OAH_APP, kmBetween } from '../lib.js'

const CITY_CENTRES = {
  Benevento: { lat: 41.1291, lon: 14.7868 }, Coimbra: { lat: 40.2033, lon: -8.4103 },
  Ghent: { lat: 51.0543, lon: 3.7174 }, Oslo: { lat: 59.9139, lon: 10.7522 }, Toulouse: { lat: 43.6047, lon: 1.4442 },
}

export default function Near({ data }) {
  const [here, setHere] = useState(null)
  const [label, setLabel] = useState('')
  const [message, setMessage] = useState('')

  const locate = () => {
    if (!navigator.geolocation) return setMessage('This browser cannot share a location. Pick a city instead.')
    setMessage('Finding where you are…')
    navigator.geolocation.getCurrentPosition(
      (p) => { setHere({ lat: p.coords.latitude, lon: p.coords.longitude }); setLabel('you'); setMessage('') },
      () => setMessage('Your location was not shared. Pick a city instead.'),
    )
  }

  const nearest = useMemo(() => {
    if (!here) return []
    const research = data.streams.map((s) => ({ ...s, km: kmBetween(here, s) }))
    const citizen = data.citizenSites.filter((s) => !s.looksLikeTest)
      .map((s) => ({ ...s, citizen: true, km: kmBetween(here, s) }))
    return [...research, ...citizen].sort((a, b) => a.km - b.km).slice(0, 8)
  }, [here, data])

  return (
    <>
      <section className="hero">
        <h1>A stream near you may need a look</h1>
        <p className="lead">
          A stream check takes a few minutes: you look at the water, the banks and the plants, and answer questions
          in the OneAquaHealth app. Find the stream closest to you that most needs one.
        </p>
        <div className="buttons">
          <button className="primary" onClick={locate}>Use my location</button>
          {Object.entries(CITY_CENTRES).map(([name, centre]) => (
            <button key={name} className="chip" aria-pressed={label === name}
              onClick={() => { setHere(centre); setLabel(name); setMessage('') }}>{name}</button>
          ))}
        </div>
        {message && <p className="small" role="status">{message}</p>}
      </section>

      {here && (
        <div className="split">
          <StreamMap streams={nearest.filter((s) => !s.citizen)} citizenSites={nearest.filter((s) => s.citizen)}
            onPick={(s) => { window.location.hash = `/stream/${s.code}` }} />
          <ol className="list" aria-label="Nearest streams">
            {nearest.map((s) => (
              <li key={s.code}>
                {s.citizen ? (
                  <div className="citizen">
                    <div className="row"><strong>{s.name}</strong><span className="tag">Added by a citizen</span></div>
                    <span className="where">{s.km.toFixed(1)} km from {label === 'you' ? 'you' : `the centre of ${label}`}</span>
                    <span className="why">No lab data exists for this stream. A citizen check is the only information.</span>
                  </div>
                ) : (
                  <a href={`#/stream/${s.code}`}>
                    <div className="row"><strong>{s.name}</strong><Badge level={s.level} /></div>
                    <span className="where">{s.km.toFixed(1)} km from {label === 'you' ? 'you' : `the centre of ${label}`} · {s.city}</span>
                    <span className="why">{s.lab ? `Last lab check ${s.lab.age}.` : 'No lab result on record.'}</span>
                  </a>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}

      <section className="panel cta">
        <h2>Ready to check a stream?</h2>
        <p>The check itself happens in OneAquaHealth's own Citizen Science App. Stream Check-up only tells you where one is most needed.</p>
        <a className="primary" href={OAH_APP} target="_blank" rel="noreferrer">Open the OneAquaHealth app</a>
      </section>
    </>
  )
}
