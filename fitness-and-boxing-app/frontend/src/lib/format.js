export const GOALS = {
  boxing: { label: 'Boxing', blurb: 'Skills, rounds and fight conditioning' },
  strength: { label: 'Strength', blurb: 'Get stronger on the big lifts' },
  fat_loss: { label: 'Fat loss', blurb: 'Burn it off with circuits and lifting' },
  general: { label: 'General fitness', blurb: 'A bit of everything, boxing included' },
}

export const LEVELS = {
  beginner: { label: 'Beginner', blurb: 'New, or back after a long break' },
  intermediate: { label: 'Intermediate', blurb: 'Training regularly' },
  advanced: { label: 'Advanced', blurb: 'Years of consistent training' },
}

export const EQUIPMENT = {
  bodyweight: { label: 'No equipment', blurb: 'Just you and some floor' },
  home: { label: 'Home kit', blurb: 'Dumbbells, bands, a kettlebell' },
  full_gym: { label: 'Full gym', blurb: 'Barbells, machines, cables' },
}

export const BODY_PARTS = [
  'Abdominals', 'Abductors', 'Adductors', 'Biceps', 'Calves', 'Chest', 'Forearms', 'Glutes',
  'Hamstrings', 'Lats', 'Lower Back', 'Middle Back', 'Neck', 'Quadriceps', 'Shoulders',
  'Traps', 'Triceps',
]

export const RATINGS = [
  { value: 1, label: 'Too easy' },
  { value: 2, label: 'Easy' },
  { value: 3, label: 'About right' },
  { value: 4, label: 'Hard' },
  { value: 5, label: 'Too hard' },
]

export const PUNCHES = [
  ['1', 'Jab'], ['2', 'Cross'], ['3', 'Lead hook'],
  ['4', 'Rear hook'], ['5', 'Lead uppercut'], ['6', 'Rear uppercut'],
]

// Local date, not toISOString(), which is UTC and gives the wrong day near midnight.
export function isoToday(now = new Date()) {
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${m}-${d}`
}

export const parseDay = (iso) => new Date(`${iso}T00:00:00`)

export function fmtDate(iso, opts = { weekday: 'short', day: 'numeric', month: 'short' }) {
  return parseDay(iso).toLocaleDateString(undefined, opts)
}

export function relativeDay(iso, today = isoToday()) {
  const days = Math.round((parseDay(iso) - parseDay(today)) / 86400000)
  if (days === 0) return 'Today'
  if (days === 1) return 'Tomorrow'
  if (days === -1) return 'Yesterday'
  if (days < 0) return `${-days} days ago`
  if (days < 7) return fmtDate(iso, { weekday: 'long' })
  return fmtDate(iso)
}

export function clock(seconds) {
  const s = Math.max(0, Math.ceil(seconds))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

export function mmss(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m && !s) return `${m} min`
  return m ? `${m}:${String(s).padStart(2, '0')}` : `${s}s`
}

export function prescription(e) {
  if (e.duration_seconds) {
    return e.sets > 1 ? `${e.sets} × ${mmss(e.duration_seconds)}` : mmss(e.duration_seconds)
  }
  if (e.reps) return `${e.sets} × ${e.reps}`
  return `${e.sets} sets`
}

// The model's 0-2 expected difficulty, in words.
export function difficultyLabel(score) {
  if (score == null) return null
  if (score < 0.7) return 'Beginner-friendly'
  if (score < 1.3) return 'Moderate'
  return 'Demanding'
}

export function intensityWords(value) {
  if (value > 1.01) return `${Math.round((value - 1) * 100)}% harder`
  if (value < 0.99) return `${Math.round((1 - value) * 100)}% easier`
  return 'Holding steady'
}
