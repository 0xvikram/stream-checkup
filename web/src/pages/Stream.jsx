import { useEffect, useState } from 'react'
import Badge from '../Badge.jsx'
import StreamMap from '../StreamMap.jsx'
import { listVisitRequests, sendVisitRequest, visitRequest } from '../fhir.js'
import { LEVELS, OAH_APP, distanceText, longDate, monthYear } from '../lib.js'

const LAB_PARTS = [
  ['germs', 'Germs that can make people ill'],
  ['sewage', 'Signs of sewage'],
  ['resistant', 'Bacteria that resist antibiotics'],
]

function RainChart({ months }) {
  const top = Math.max(...months.map((m) => m.rain), 1)
  const w = 100 / months.length
  return (
    <figure className="chart">
      <svg viewBox="0 0 100 34" preserveAspectRatio="none" role="img"
        aria-label={`Rain per month from ${monthYear(months[0].m)} to ${monthYear(months.at(-1).m)}`}>
        {months.map((m, i) => (
          <rect key={m.m} x={i * w + w * 0.12} width={w * 0.76} y={32 - (m.rain / top) * 30}
            height={Math.max((m.rain / top) * 30, 0.4)} rx="0.4" className={m.heavy ? 'heavy' : ''}>
            <title>{`${monthYear(m.m)}: ${m.rain} mm of rain, ${m.heavy} heavy-rain day${m.heavy === 1 ? '' : 's'}`}</title>
          </rect>
        ))}
      </svg>
      <figcaption>
        <span>{monthYear(months[0].m)}</span>
        <span className="key"><i className="heavy" /> month with heavy rain <i /> other months</span>
        <span>{monthYear(months.at(-1).m)}</span>
      </figcaption>
    </figure>
  )
}

function VisitRequest({ stream }) {
  const [state, setState] = useState({ step: 'idle' })
  const [open, setOpen] = useState(null) // a request already waiting for this stream
  useEffect(() => {
    setState({ step: 'idle' })
    setOpen(null)
    listVisitRequests()
      .then((all) => setOpen(all.find((r) => r.code === stream.code && !r.done) || null))
      .catch(() => {}) // the card still works if the test system is unreachable
  }, [stream.code])
  const send = async () => {
    setState({ step: 'sending' })
    try {
      setState({ step: 'sent', ...(await sendVisitRequest(stream)) })
    } catch (e) {
      setState({ step: 'failed', message: e.message })
    }
  }
  return (
    <section className="panel action">
      <h2>What to do</h2>
      <p>
        {stream.level === 'wait'
          ? 'This stream has the fewest reasons to look again. A visit is still welcome.'
          : 'Ask a volunteer to visit this stream and carry out a stream check.'}
      </p>
      <div className="buttons">
        {state.step !== 'sent' && !open && (
          <button className="primary" onClick={() => setState({ step: 'review' })} disabled={state.step === 'sending'}>
            Ask for a visit
          </button>
        )}
        <a className="secondary" href={OAH_APP} target="_blank" rel="noreferrer">Do the check yourself in the OneAquaHealth app</a>
      </div>
      {open && state.step !== 'sent' && (
        <p className="done">
          A visit was asked for on {longDate(open.askedOn)} and is waiting. <a href="#/requests">See all requests</a>
        </p>
      )}
      {(state.step === 'review' || state.step === 'sending') && (
        <div className="review">
          <p><strong>This request will be sent to OneAquaHealth's test system:</strong></p>
          <p className="quote">
            Please visit {stream.name}, {stream.city} ({stream.code}).{' '}
            {stream.lab ? `Its last lab check was on ${longDate(stream.lab.date)}.` : 'It has no lab result on record.'}{' '}
            Reasons: {stream.factors.filter((f) => f.points > 0).map((f) => f.title.toLowerCase()).join(', ') || 'routine re-check'}.
          </p>
          <p className="small">A person at OneAquaHealth decides whether the visit happens. Nothing is changed in their records.</p>
          <div className="buttons">
            <button className="primary" onClick={send} disabled={state.step === 'sending'}>
              {state.step === 'sending' ? 'Sending…' : 'Send the request'}
            </button>
            <button className="plain" onClick={() => setState({ step: 'idle' })}>Cancel</button>
          </div>
          <details>
            <summary>For the data team: the request in the health-data standard</summary>
            <pre>{JSON.stringify(visitRequest(stream), null, 2)}</pre>
          </details>
        </div>
      )}
      {state.step === 'sent' && (
        <p className="done">
          Request sent. It is now in OneAquaHealth's test system as record {state.id}.{' '}
          <a href={state.url} target="_blank" rel="noreferrer">See the record</a> · <a href="#/requests">See all requests</a>
        </p>
      )}
      {state.step === 'failed' && <p className="failed">The request could not be sent. {state.message}. Please try again.</p>}
    </section>
  )
}

export default function Stream({ data, code }) {
  const stream = data.streams.find((s) => s.code === code)
  if (!stream) return <p className="notice">No stream with the code {code}. <a href="#/">Back to all streams</a></p>
  const { lab, since, near } = stream
  const inCity = data.streams.filter((s) => s.city === stream.city).length

  return (
    <article className="stream">
      <a className="back" href="#/">← All streams</a>
      <header className="streamhead">
        <div>
          <h1>{stream.name}</h1>
          <p className="where">{stream.city} · site {stream.code}</p>
        </div>
        <div className="verdict">
          <Badge level={stream.level} big />
          <span>{LEVELS[stream.level].note} · number {stream.cityRank} of {inCity} in {stream.city}</span>
        </div>
      </header>

      <div className="cols">
        <div>
          <section className="panel">
            <h2>How old is what we know?</h2>
            {lab ? (
              <>
                <p className="fact">Last lab check: <strong>{longDate(lab.date)}</strong> ({lab.age}).</p>
                <p className="small">What the lab found then, compared with the other streams:</p>
                <ul className="bars">
                  {LAB_PARTS.map(([key, label]) => (
                    <li key={key}>
                      <span>{label}</span>
                      <span className="bar" role="img" aria-label={`${Math.round(lab[key] * 100)} out of 100`}>
                        <i style={{ width: `${Math.max(lab[key] * 100, 2)}%` }} />
                      </span>
                    </li>
                  ))}
                </ul>
                <p className="scale"><span>lower</span><span>higher</span></p>
              </>
            ) : (
              <p className="fact">There is <strong>no lab result on record</strong> for this stream. Nothing is known about its water.</p>
            )}
          </section>

          {since && (
            <section className="panel">
              <h2>What has happened since?</h2>
              <ul className="facts">
                <li><b>{since.heavyRainDays}</b> days of heavy rain</li>
                <li><b>{since.hotDays}</b> days at 30 °C or more</li>
                <li><b>{since.heatwaves}</b> heatwaves</li>
              </ul>
              <p className="small">
                Wettest day: {longDate(since.wettestDay.date)} ({since.wettestDay.mm} mm). Hottest day:{' '}
                {longDate(since.hottestDay.date)} ({since.hottestDay.c} °C).
              </p>
              <RainChart months={stream.monthly} />
              <p className="small">
                Counted from {longDate(since.from)} to {longDate(since.to)}, the newest weather day on record.
                {!lab && ' With no lab check to count from, this covers all the weather on record.'}
              </p>
            </section>
          )}

          {near && (
            <section className="panel">
              <h2>What is around it?</h2>
              <ul className="facts">
                <li><b>{distanceText(near.sewageM)}</b> to the nearest sewage works</li>
                <li><b>{distanceText(near.hospitalM)}</b> to the nearest hospital</li>
                <li><b>{Math.round(near.pavedPct)}%</b> paved or built over, within 250 m</li>
                <li><b>{Math.round(near.greenPct)}%</b> green cover, within 250 m</li>
              </ul>
            </section>
          )}
        </div>

        <div>
          <section className="panel why">
            <h2>Why this level?</h2>
            <ul>
              {stream.factors.map((f) => (
                <li key={f.key}>
                  <span className="pips" aria-label={`${f.points} of 2 points`}>
                    {[0, 1].map((i) => <i key={i} className={i < f.points ? 'on' : ''} />)}
                  </span>
                  <div><strong>{f.title}</strong><p>{f.text}</p></div>
                </li>
              ))}
            </ul>
            <p className="small">
              {lab
                ? `${stream.points} of 8 points. 6 or more means check first, 3 to 5 check soon, 2 or fewer can wait.`
                : 'A stream with no lab result is always listed as never checked.'}{' '}
              <a href="#/how">How the levels work</a>
            </p>
          </section>
          <VisitRequest stream={stream} />
          <StreamMap streams={[stream]} selected={stream.code} height={260} />
        </div>
      </div>
    </article>
  )
}
