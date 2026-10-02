import { longDate } from '../lib.js'

export default function How({ data }) {
  const { counts } = data
  return (
    <article className="prose">
      <h1>How it works</h1>
      <p className="lead">
        Stream Check-up predicts nothing. It lines up four facts that OneAquaHealth already holds about each stream
        and shows which streams have the most reasons to be looked at again.
      </p>

      <h2>The four facts</h2>
      <table>
        <thead><tr><th>Fact</th><th>Where it comes from</th><th>More points when</th></tr></thead>
        <tbody>
          <tr><td>Last lab result</td><td>OneAquaHealth lab health-risk score</td><td>the risk was higher</td></tr>
          <tr><td>Heavy rain since then</td><td>Days with 20 mm of rain or more, OneAquaHealth weather data</td><td>there were more such days</td></tr>
          <tr><td>Hot days since then</td><td>Days reaching 30 °C or more, OneAquaHealth weather data</td><td>there were more such days</td></tr>
          <tr><td>Sewage works nearby</td><td>Distance to the nearest sewage works, OneAquaHealth site data</td><td>it is closer</td></tr>
        </tbody>
      </table>
      <p>
        For each fact, all {counts.streams} streams are split into three equal groups: lower, middle and upper.
        A stream gets 0, 1 or 2 points per fact, so 8 at most.
      </p>
      <ul>
        <li><strong>Check first:</strong> 6 points or more.</li>
        <li><strong>Check soon:</strong> 3 to 5 points.</li>
        <li><strong>Can wait:</strong> 2 points or fewer.</li>
        <li><strong>Never checked:</strong> no lab result on record, whatever the points.</li>
      </ul>

      <h2>Why not predict stream health from maps?</h2>
      <p>
        We tested it. For the {counts.withLab} streams with a lab result, we hid each one in turn and estimated its
        health risk from the streams with the most similar surroundings (paved area, green cover, distance to sewage
        works, and 50 more measures). The estimate was no better than guessing the average for every stream.
      </p>
      <p>
        So surroundings alone cannot tell you how a stream is doing. Someone has to go and look, which is the
        reason citizen checks matter and the reason this tool ranks visits and does not guess results.
      </p>

      <h2>What this tool cannot tell you</h2>
      <ul>
        <li>It does not say a stream is unhealthy today. It says how much reason there is to look again.</li>
        <li>The cut-offs (20 mm, 30 °C, the point levels) are simple choices and have not been tested against new lab results, because none exist yet.</li>
        <li>Weather is almost the same for every stream in one city, so it mostly separates cities. Inside a city, the order comes from the last lab result and the distance to a sewage works.</li>
        <li>Hot days are counted against a fixed 30 °C, so warmer cities score higher on that fact.</li>
        <li>Citizen checks made in the OneAquaHealth app are not public, so they are not included.</li>
        <li>The lab scores compare streams with each other. They are not safety limits.</li>
      </ul>

      <h2>Where the data comes from</h2>
      <ul>
        <li>Streams, lab results, surroundings and weather: the public service behind the OneAquaHealth Resilience Map.</li>
        <li>Records checked on the "Record problems" page: the OneAquaHealth test system for health data (HL7 Europe sandbox).</li>
        <li>Copied on {longDate(data.snapshot)}. Running one command refreshes it.</li>
      </ul>

      <h2>How OneAquaHealth could use it</h2>
      <ul>
        <li>Run it next to the Resilience Map: it reads the same data and needs no login.</li>
        <li>Visit requests arrive in the health-data standard the project already uses, so they can be picked up by any system that reads it.</li>
        <li>It costs nothing to host: the site is a set of plain files.</li>
      </ul>
    </article>
  )
}
