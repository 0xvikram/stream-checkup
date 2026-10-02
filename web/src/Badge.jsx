import { LEVELS } from './lib.js'

export default function Badge({ level, big }) {
  const { label, color } = LEVELS[level]
  return (
    <span className={`badge${big ? ' big' : ''}`} style={{ '--c': color }}>
      <span className="dot" aria-hidden="true" />
      {label}
    </span>
  )
}
