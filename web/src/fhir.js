// A visit request, written in the health-data standard OneAquaHealth already uses (HL7 FHIR R4).
// It is a proposal: a person at OneAquaHealth decides whether the visit happens.

export const SANDBOX = 'https://sandbox.hl7europe.eu/oneaquahealth/fhir'
const SITE_CODES = 'https://api.enora-oah.eu/api/sites'
const TAG = { system: 'urn:stream-checkup:tags', code: 'visit-request', display: 'Stream Check-up visit request' }
const HEADERS = { 'Content-Type': 'application/fhir+json', Accept: 'application/fhir+json' }
// The sandbox answers browsers with two "allow origin" headers, which browsers reject.
// Calls go through a relay on our own address instead (vite.config.js locally, vercel.json when deployed).
const RELAY = '/fhir-relay'

export function visitRequest(stream, today = new Date()) {
  return {
    resourceType: 'ServiceRequest',
    meta: { tag: [TAG] },
    status: 'active',
    intent: 'proposal',
    priority: stream.level === 'first' || stream.level === 'never' ? 'urgent' : 'routine',
    code: { text: 'Visit this stream and carry out a OneAquaHealth citizen stream check' },
    subject: {
      ...(stream.fhirId ? { reference: `Location/${stream.fhirId}` } : {}),
      type: 'Location',
      identifier: { system: SITE_CODES, value: stream.code },
      display: `${stream.name}, ${stream.city}`,
    },
    authoredOn: today.toISOString(),
    requester: { display: 'Stream Check-up' },
    reasonCode: stream.factors.map((f) => ({ text: `${f.title}: ${f.text}` })),
    note: [{
      text: stream.lab
        ? `Last lab check ${stream.lab.date}. Reasons scored ${stream.points} of 8.`
        : 'No lab result on record for this stream.',
    }],
  }
}

async function call(path, options) {
  const response = await fetch(`${RELAY}/${path}`, { headers: HEADERS, ...options })
  if (!response.ok) throw new Error(`The test system answered ${response.status}`)
  return response.json()
}

export async function sendVisitRequest(stream) {
  const saved = await call('ServiceRequest', { method: 'POST', body: JSON.stringify(visitRequest(stream)) })
  return { id: saved.id, url: `${SANDBOX}/ServiceRequest/${saved.id}` }
}

// Every visit request Stream Check-up has sent, newest first, read live.
export async function listVisitRequests() {
  const bundle = await call(`ServiceRequest?_tag=${encodeURIComponent(`${TAG.system}|${TAG.code}`)}&_sort=-_lastUpdated&_count=200`)
  return (bundle.entry || []).map(({ resource }) => ({
    id: resource.id,
    code: resource.subject?.identifier?.value,
    place: resource.subject?.display,
    askedOn: resource.authoredOn,
    done: resource.status === 'completed',
    doneOn: resource.status === 'completed' ? resource.meta?.lastUpdated : null,
    urgent: resource.priority === 'urgent',
    url: `${SANDBOX}/ServiceRequest/${resource.id}`,
    resource,
  }))
}

// Close the loop: the visit happened.
export async function markVisited(request) {
  const { meta, ...rest } = request.resource
  await call(`ServiceRequest/${request.id}`, {
    method: 'PUT',
    body: JSON.stringify({ ...rest, meta: { tag: meta?.tag }, status: 'completed' }),
  })
}
