import Badge from '../Badge.jsx'
import { distanceText, longDate } from '../lib.js'

// One printable page per city, for a meeting.
export default function Brief({ data, city }) {
  const streams = data.streams.filter((s) => s.city === city)
  if (!streams.length) return <p className="notice">No streams on record for {city}. <a href="#/">Back</a></p>
  const count = (level) => streams.filter((s) => s.level === level).length
  const top = streams.filter((s) => s.level === 'first' || s.level === 'never').slice(0, 10)
  const labDates = streams.filter((s) => s.lab).map((s) => s.lab.date).sort()
  const since = streams.find((s) => s.since)?.since

  return (
    <article className="brief">
      <div className="noprint buttons">
        <a className="back" href="#/">← All streams</a>
        <button className="primary" onClick={() => window.print()}>Print this page</button>
      </div>
      <p className="where">Stream Check-up · city brief · data copied on {longDate(data.snapshot)}</p>
      <h1>{city}: which streams to look at first</h1>

      <ul className="facts">
        <li><b>{streams.length}</b> streams watched</li>
        <li><b>{count('never')}</b> never checked</li>
        <li><b>{count('first')}</b> to check first</li>
        <li><b>{count('soon')}</b> to check soon</li>
        <li><b>{count('wait')}</b> can wait</li>
      </ul>

      <p>
        {labDates.length > 0
          ? <>The lab results for {city} date from {longDate(labDates[0])}{labDates.at(-1) !== labDates[0] && <> to {longDate(labDates.at(-1))}</>}. </>
          : <>There are no lab results on record for {city}. </>}
        {since && <>Since then the city has had about {since.heavyRainDays} days of heavy rain and {since.hotDays} days at 30 °C or more.</>}
      </p>

      <h2>Start with these</h2>
      {top.length === 0 ? <p>No stream in {city} is in the top group. See the full list for the order.</p> : (
        <table>
          <thead><tr><th>#</th><th>Stream</th><th>Level</th><th>Last lab check</th><th>Main reasons</th></tr></thead>
          <tbody>
            {top.map((s) => (
              <tr key={s.code}>
                <td>{s.cityRank}</td>
                <td><strong>{s.name}</strong><br /><span className="where">{s.code}</span></td>
                <td><Badge level={s.level} /></td>
                <td>{s.lab ? longDate(s.lab.date) : 'None on record'}</td>
                <td>
                  {s.lab ? s.factors.filter((f) => f.points === 2).map((f) => f.title.toLowerCase()).join('; ') || 'several medium reasons'
                    : 'nothing is known about this stream'}
                  {s.near && <>. Sewage works {distanceText(s.near.sewageM)} away</>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2>What this brief does not say</h2>
      <p>
        It does not say these streams are unhealthy today. It says they have the most reasons to be looked at again.
        Only a visit or a new lab sample can tell how a stream is doing now.
      </p>
    </article>
  )
}
