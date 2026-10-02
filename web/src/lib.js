import { useEffect, useState } from 'react'

export const OAH_APP = 'https://apps.oneaquahealth.eu/login'

export const LEVELS = {
  never: { label: 'Never checked', color: '#5B4BB7', note: 'No lab result on record' },
  first: { label: 'Check first', color: '#B42318', note: 'Most reasons to look again' },
  soon: { label: 'Check soon', color: '#B45309', note: 'Some reasons to look again' },
  wait: { label: 'Can wait', color: '#1B7F5A', note: 'Fewest reasons to look again' },
}
export const LEVEL_ORDER = ['never', 'first', 'soon', 'wait']

export function useData() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => {
    fetch('./data.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`data.json: ${r.status}`))))
      .then(setData)
      .catch(setError)
  }, [])
  return { data, error }
}

export function useRoute() {
  const read = () => window.location.hash.replace(/^#/, '') || '/'
  const [route, setRoute] = useState(read)
  useEffect(() => {
    const onChange = () => {
      setRoute(read())
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}

export function longDate(iso) {
  return new Date(`${iso.slice(0, 10)}T00:00:00Z`).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC',
  })
}

export function monthYear(iso) {
  return new Date(`${iso.slice(0, 7)}-01T00:00:00Z`).toLocaleDateString('en-GB', {
    month: 'long', year: 'numeric', timeZone: 'UTC',
  })
}

export function distanceText(metres) {
  return metres >= 1000 ? `${(metres / 1000).toFixed(1)} km` : `${Math.round(metres / 10) * 10} m`
}

export function kmBetween(a, b) {
  const rad = (d) => (d * Math.PI) / 180
  const dLat = rad(b.lat - a.lat)
  const dLon = rad(b.lon - a.lon)
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLon / 2) ** 2
  return 6371 * 2 * Math.asin(Math.sqrt(h))
}

// The single strongest reason, for the one-line summary in lists.
export function mainReason(stream) {
  if (!stream.lab) return 'No lab result on record for this stream.'
  const top = [...stream.factors].sort((a, b) => b.points - a.points)[0]
  return top.text.split('. ')[0] + '.'
}
