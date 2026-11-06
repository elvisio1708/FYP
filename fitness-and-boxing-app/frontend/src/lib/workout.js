// Turns a session's exercise list into the ordered steps the workout timer plays.
//
// Step shape:
//   phase    'warmup' | 'work' | 'cooldown' | 'rest'
//   seconds  countdown length, or null for rep-based sets (user taps "Set done")
//   round / rounds  position within the session's boxing rounds, when boxing
//   set / sets      position within the exercise otherwise
//   next     title of the following step, for the "up next" line

function workStep(e, extra) {
  return {
    phase: e.kind === 'warmup' || e.kind === 'cooldown' ? e.kind : 'work',
    kind: e.kind,
    title: e.name.replace(/^Circuit: /, ''),
    description: e.description || '',
    notes: e.kind === 'gym' ? e.notes || '' : '',
    seconds: e.duration_seconds || null,
    reps: e.reps || null,
    ...extra,
  }
}

const restStep = (seconds) => ({ phase: 'rest', title: 'Rest', seconds })

export function buildSteps(exercises) {
  const steps = []
  let i = 0
  while (i < exercises.length) {
    const e = exercises[i]

    if (e.circuit) {
      // Stations run in order, then the whole loop repeats. They are stored as
      // separate exercises, so playing them one by one would do all the skipping
      // first, then all the burpees.
      const stations = []
      while (exercises[i]?.circuit) stations.push(exercises[i++])
      const loops = stations[0].sets || 1
      for (let loop = 1; loop <= loops; loop++) {
        stations.forEach((station, n) => {
          steps.push(workStep(station, { loop, loops, station: n + 1, stations: stations.length }))
          const last = loop === loops && n === stations.length - 1
          if (station.rest_seconds && !last) steps.push(restStep(station.rest_seconds))
        })
      }
      continue
    }

    const sets = e.sets || 1
    for (let set = 1; set <= sets; set++) {
      steps.push(workStep(e, { set, sets }))
      const following = exercises[i + 1]
      const moreOfSameBlock = set < sets || following?.kind === e.kind
      if (e.rest_seconds && moreOfSameBlock) steps.push(restStep(e.rest_seconds))
    }
    i++
  }

  const rounds = steps.filter((s) => s.kind === 'boxing' && !s.loop).length
  let round = 0
  steps.forEach((step, n) => {
    if (step.kind === 'boxing' && !step.loop) {
      step.round = ++round
      step.rounds = rounds
    }
    step.next = steps.slice(n + 1).find((s) => s.phase !== 'rest')?.title ?? null
  })
  return steps
}

// Rep-based sets have no fixed length; ~4 s a rep matches the backend's estimate.
export const stepSeconds = (s) => s.seconds ?? (s.reps || 10) * 4

export const totalSeconds = (steps) => steps.reduce((sum, s) => sum + stepSeconds(s), 0)

export function stepLabel(step) {
  if (step.phase === 'rest') return 'Rest'
  if (step.phase === 'warmup') return 'Warm-up'
  if (step.phase === 'cooldown') return 'Cool-down'
  if (step.loop) return `Round ${step.loop} of ${step.loops} · Station ${step.station} of ${step.stations}`
  if (step.round) return `Round ${step.round} of ${step.rounds}`
  return `Set ${step.set} of ${step.sets}`
}
