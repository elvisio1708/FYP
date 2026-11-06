// Which session matters now. Plans run on calendar dates but real weeks slip, so
// a miss from long ago must not block the sessions that are actually coming up.
export const CATCH_UP_DAYS = 3

const daysBetween = (from, to) => Math.round((new Date(`${to}T00:00:00`) - new Date(`${from}T00:00:00`)) / 86400000)

export function isMissed(session, today) {
  return !session.completed && daysBetween(session.scheduled_for, today) > CATCH_UP_DAYS
}

export function nextSession(sessions, today) {
  const open = sessions.filter((s) => !s.completed)
  return (
    open.find((s) => s.scheduled_for === today) ??
    open.find((s) => !isMissed(s, today)) ??
    open[open.length - 1] ?? // only old misses are left: offer the latest
    null
  )
}

// The plan week holding `today`, clamped to the plan's range.
export function currentWeek(sessions, startDate, today) {
  const weeks = sessions.map((s) => s.week)
  if (!weeks.length) return null
  const week = Math.floor(daysBetween(startDate, today) / 7) + 1
  return Math.min(Math.max(week, Math.min(...weeks)), Math.max(...weeks))
}
