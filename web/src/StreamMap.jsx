import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { LEVELS } from './lib.js'

// Streams as coloured dots. `focus` zooms to those streams; `onPick` fires on click.
export default function StreamMap({ streams, citizenSites = [], selected, onPick, height = 460 }) {
  const el = useRef(null)
  const map = useRef(null)
  const layer = useRef(null)

  useEffect(() => {
    map.current = L.map(el.current, { scrollWheelZoom: false, attributionControl: true })
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map.current)
    layer.current = L.layerGroup().addTo(map.current)
    return () => map.current.remove()
  }, [])

  useEffect(() => {
    layer.current.clearLayers()
    citizenSites.forEach((s) => {
      L.circleMarker([s.lat, s.lon], {
        radius: 5, color: '#0F5E73', weight: 2, fillColor: '#fff', fillOpacity: 1,
      }).bindTooltip(`${s.name} (added by a citizen, no lab data)`).addTo(layer.current)
    })
    streams.forEach((s) => {
      const isSelected = s.code === selected
      L.circleMarker([s.lat, s.lon], {
        radius: isSelected ? 11 : 8,
        color: isSelected ? '#10212B' : '#fff',
        weight: isSelected ? 3 : 1.5,
        fillColor: LEVELS[s.level].color,
        fillOpacity: 0.95,
      })
        .bindTooltip(`${s.name}: ${LEVELS[s.level].label}`)
        .on('click', () => onPick && onPick(s))
        .addTo(layer.current)
    })
  }, [streams, citizenSites, selected, onPick])

  // Re-frame only when the set of streams changes, not when one is selected.
  const shown = [...streams, ...citizenSites].map((s) => s.code).join(',')
  useEffect(() => {
    const points = [...streams, ...citizenSites].map((s) => [s.lat, s.lon])
    if (points.length === 1) map.current.setView(points[0], 14)
    else if (points.length) map.current.fitBounds(points, { padding: [28, 28], maxZoom: 13 })
  }, [shown])

  return <div ref={el} className="map" style={{ height }} role="img" aria-label="Map of streams, coloured by how soon each needs a check" />
}
