# Stream Check-up

**Which city streams are overdue for a look, why, and which records cannot be trusted.**

Built for the OneAquaHealth IEEE Global Hackathon 2026 · **Track 2: Data-to-Insight**

**Live:** https://stream-checkup.vercel.app · **Record problems:** https://stream-checkup.vercel.app/#/records

## The problem

OneAquaHealth watches 106 urban streams in five European cities. Its own public data shows:

- **95 of the 96 lab health-risk results are from 2023.** Each stream was sampled once.
- **10 research streams have no lab result at all**, but look the same as the others on the map.
- **51 lab records hold numbers no stream can have**, such as a pH of 83,800.

Cities decide where to act using this picture. It is three years old, and some of it is wrong.

## What Stream Check-up does

It answers three questions about every stream, in plain words, and ends with one action.

| Question | What the page shows | Source |
|---|---|---|
| How old is what we know? | Date and result of the last lab check | OneAquaHealth lab results |
| What has happened since? | Days of heavy rain, hot days, heatwaves | OneAquaHealth weather data |
| Can we trust the record? | Records that break simple rules | OneAquaHealth health-data test system |

Each stream gets one of four levels: **Never checked**, **Check first**, **Check soon**, **Can wait**.
Every level comes with its reasons, written as sentences.

The action is a **visit request**: one click sends a request to OneAquaHealth's own test system, in the
health-data standard the project already uses (HL7 FHIR). A person there decides whether the visit happens.
The **Visit requests** page reads them back live and lets a coordinator mark each one as visited.

It also acts on the record problems it can safely act on:

- **Links the two systems.** Each research stream is added to the health-data system carrying the code the
  map data uses, so a result in one can be matched to a stream in the other.
- **Pins a note to each impossible value.** The note states the likely correction and asks for confirmation.
  The original record is never changed.
- **Watches nightly.** A scheduled job re-reads the public data every night and the home page lists what
  changed since the last check.
- **Prints a city brief.** One page per city for a meeting.

## Who it is for

- **City and project coordinators** deciding where to send volunteers or the lab next.
- **The OneAquaHealth data team**, who get a list of record problems with links to each record.
- **Citizens**, who can find the stream near them that most needs a check, then do it in the
  existing Citizen Science App.

## Track alignment

Track 2 asks for stream data that is "hard to interpret" to be turned into "actionable stream health and
One Health insights". Stream Check-up turns four existing data sets into one ranked list with reasons and
an action. The lab results it uses measure germs that make people ill, signs of sewage, and bacteria that
resist antibiotics, which is the link between stream health and human health.

## How the levels work

Four facts per stream, all taken from OneAquaHealth's data. Nothing is predicted.

1. The last lab health-risk result.
2. Days with 20 mm of rain or more since that result.
3. Days reaching 30 °C or more since that result.
4. Distance to the nearest sewage works.

For each fact, the streams are split into three equal groups, worth 0, 1 or 2 points. Six points or more
means check first, three to five check soon, two or fewer can wait. A stream with no lab result is always
"Never checked".

### Why not predict stream health from maps?

We tested it. For the 96 streams with a lab result, we hid each one in turn and estimated its risk from
the five streams with the most similar surroundings (53 measures of paved area, green cover and distances).

| Method | Average error (risk score runs 0 to 1) |
|---|---|
| Guess the overall average | 0.101 |
| Guess the city average | 0.095 |
| Five most similar streams | 0.104 |

Run `python3 scripts/twin_test.py` to repeat it. Surroundings alone do no better than guessing. Someone has to go and look, so this tool ranks visits and
does not guess results.

## Record problems found

All counts are from the snapshot of 3 October 2026 and are recomputed on every build.

| Count | Problem | Who fixes it |
|---|---|---|
| 51 | Measurements that cannot be real (values about 10,000 times too large) | OneAquaHealth data team |
| 12 | Different places recorded on the same map point | OneAquaHealth data team |
| 5 | Places with no position | OneAquaHealth data team |
| 104 | Streams with no shared name between the two systems | Stream Check-up |
| 9 | Try-out entries on the public list of citizen streams | Stream Check-up |
| 10 | Research streams with no lab result | Stream Check-up |
| 2 | Research streams with an empty name | OneAquaHealth data team |
| 1 | The health-data system answers web pages with two "allow" headers, so browsers refuse it | OneAquaHealth data team |

## How it is built

```
scripts/fetch.py     copies OneAquaHealth's public data into data/raw/
scripts/checkup.py   the rules: levels, reasons, record checks (no network, fully tested)
scripts/build.py     writes web/public/data.json and one summary per day in data/history/
scripts/fhir.py      the records we write (stream links, pinned notes), as pure builders
scripts/publish.py   sends them; prints a dry run unless given --send; never creates duplicates
scripts/twin_test.py the "can maps predict stream health" test
tests/               30 tests on the rules and the records
web/                 the site (React, Vite, Leaflet with OpenStreetMap)
.github/workflows/   nightly.yml (the watchdog), validate.yml (official HL7 validator)
```

The site is plain files and needs no login. The only live calls are visit requests. They pass through a
small relay on the site's own address (`vercel.json`), limited to that one record type, because the
sandbox cannot be read from a browser directly.

**Data sources:** `api.enora-oah.eu` (the public service behind the Resilience Map) and
`sandbox.hl7europe.eu/oneaquahealth/fhir` (the HL7 Europe sandbox).

## Run it

```bash
python3 scripts/fetch.py        # refresh the snapshot (about 5 minutes)
python3 scripts/build.py        # rebuild web/public/data.json
python3 -m unittest discover -s tests
python3 scripts/publish.py      # dry run: writes the records to data/fhir-out/
python3 scripts/publish.py --send   # sends them to the sandbox

cd web
npm install
npm run dev                     # http://localhost:5173
```

## How OneAquaHealth could adopt it

- Host the `web/dist` folder next to the Resilience Map. It reads the same data.
- Run `fetch.py` and `build.py` on a schedule to keep it current.
- Read visit requests from the FHIR server as `ServiceRequest` records tagged `visit-request`.

## Limits

- It does not say a stream is unhealthy today. It says how much reason there is to look again.
- The cut-offs (20 mm, 30 °C, the point levels) are simple choices. They have not been tested against new
  lab results, because none exist yet.
- Weather is almost the same for every stream in one city, so it mostly separates cities. Inside a city the
  order comes from the last lab result and the distance to a sewage works.
- Hot days are counted against a fixed 30 °C, so warmer cities score higher on that fact.
- Citizen checks made in the OneAquaHealth app are not public, so they are not included.
- The suggested corrections for impossible values are guesses. Someone with the original lab sheet must confirm them.
- No coordinator or citizen has used the tool yet.
- The nightly job and the validator run on GitHub. Their results are in the Actions tab, not in this file.

## Credits

Data from the OneAquaHealth project (Horizon Europe grant 101086521) through its public services. Map tiles
© OpenStreetMap contributors. This is a community prototype and not an official OneAquaHealth product.
