import { useEffect, useState } from 'react'
import { listVisitRequests, markVisited } from '../fhir.js'
import { longDate } from '../lib.js'

export default function Requests() {
  const [state, setState] = useState({ step: 'loading', requests: [] })
  const load = () =>
    listVisitRequests()
      .then((requests) => setState({ step: 'ready', requests }))
      .catch((e) => setState({ step: 'failed', requests: [], message: e.message }))
  useEffect(() => { load() }, [])

  const visited = async (request) => {
    setState((s) => ({ ...s, busy: request.id }))
    try {
      await markVisited(request)
      await load()
    } catch (e) {
      setState((s) => ({ ...s, busy: null, message: e.message }))
    }
  }

  const waiting = state.requests.filter((r) => !r.done)
  const done = state.requests.filter((r) => r.done)

  return (
    <>
      <section className="hero">
        <h1>Visit requests</h1>
        <p className="lead">
          Every request sent from Stream Check-up, read live from OneAquaHealth's test system. When a volunteer has
          been to the stream, mark the request as visited.
        </p>
        {state.step === 'ready' && (
          <div className="tiles">
            <div className="tile"><b>{waiting.length}</b><span>waiting for a visit</span></div>
            <div className="tile"><b>{done.length}</b><span>visited</span></div>
          </div>
        )}
      </section>

      {state.step === 'loading' && <p className="notice">Reading requests from the test system…</p>}
      {state.step === 'failed' && <p className="failed">The requests could not be read. {state.message}.</p>}
      {state.step === 'ready' && state.requests.length === 0 && (
        <p className="notice">No requests yet. Open a stream and press "Ask for a visit". <a href="#/">See the streams</a></p>
      )}
      {state.message && state.step === 'ready' && <p className="failed">That did not work. {state.message}.</p>}

      {state.requests.length > 0 && (
        <section className="panel">
          <table className="requests">
            <thead><tr><th>Stream</th><th>Asked on</th><th>Status</th><th /></tr></thead>
            <tbody>
              {state.requests.map((r) => (
                <tr key={r.id}>
                  <td>
                    {r.code ? <a href={`#/stream/${r.code}`}>{r.place}</a> : r.place}
                    {r.urgent && !r.done && <span className="tag urgent">Check first</span>}
                  </td>
                  <td>{r.askedOn ? longDate(r.askedOn) : ''}</td>
                  <td>{r.done ? <span className="status done">Visited {longDate(r.doneOn)}</span> : <span className="status">Waiting</span>}</td>
                  <td className="act">
                    {!r.done && (
                      <button className="secondary" onClick={() => visited(r)} disabled={state.busy === r.id}>
                        {state.busy === r.id ? 'Saving…' : 'Mark as visited'}
                      </button>
                    )}
                    <a href={r.url} target="_blank" rel="noreferrer">See the record</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </>
  )
}
