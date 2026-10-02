const OWNER = {
  us: ['handled', 'Stream Check-up handles this'],
  them: ['needs', 'For the OneAquaHealth data team'],
}

export default function Records({ data }) {
  const { problems } = data
  const lead = problems.find((p) => p.key === 'impossible')
  return (
    <>
      <section className="hero">
        <h1>Can we trust the records?</h1>
        <p className="lead">
          We read OneAquaHealth's public data and checked every record against simple rules, such as "water cannot
          be hotter than 45 °C". These are the problems we found. Each one links to the real record.
        </p>
        {lead && (
          <p className="callout">
            The clearest example: one stream is recorded with a pH of <strong>{lead.examples[0].recorded}</strong>.
            The pH scale stops at 14.
          </p>
        )}
      </section>

      <div className="problems">
        {problems.map((p) => (
          <section key={p.key} className={`panel problem${p.count === 0 ? ' fixed' : ''}`}>
            <header>
              <b className="count">
                {p.was !== p.count && <s>{p.was}</s>}
                {p.count}
              </b>
              <div>
                <h2>{p.title}</h2>
                {p.count === 0
                  ? <span className="owner handled">Fixed by Stream Check-up</span>
                  : <span className={`owner ${OWNER[p.owner][0]}`}>{OWNER[p.owner][1]}</span>}
                {p.flagged > 0 && <span className="owner handled">{p.flagged} notes pinned to the records</span>}
              </div>
            </header>
            <dl>
              <dt>What we saw</dt><dd>{p.saw}</dd>
              <dt>Why it matters</dt><dd>{p.matters}</dd>
              <dt>What to do</dt><dd>{p.fix}</dd>
            </dl>
            {p.examples.length > 0 && (
              <details open={p.key === 'impossible'}>
                <summary>{p.examples.length === 1 ? 'See the example' : `See ${p.examples.length} examples`}</summary>
                <table>
                  {p.key === 'impossible' && (
                    <thead><tr><th>Record</th><th>Recorded</th><th>Likely meant</th><th /></tr></thead>
                  )}
                  <tbody>
                    {p.examples.map((e, i) => (
                      <tr key={i}>
                        <td>{e.label}</td>
                        {p.key === 'impossible'
                          ? <><td className="bad">{e.recorded}</td><td className="good">{e.likely ?? 'unclear'}</td></>
                          : <td>{e.detail}</td>}
                        <td>
                          {e.url && <a href={e.url} target="_blank" rel="noreferrer">See the record</a>}
                          {e.note && <> · <a href={e.note} target="_blank" rel="noreferrer">See our note</a></>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </details>
            )}
          </section>
        ))}
      </div>
    </>
  )
}
