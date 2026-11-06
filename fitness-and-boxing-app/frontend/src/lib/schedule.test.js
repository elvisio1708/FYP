import assert from 'node:assert/strict'
import { test } from 'node:test'
import { currentWeek, isMissed, nextSession } from './schedule.js'

const s = (id, scheduled_for, completed = false, week = 1) => ({ id, scheduled_for, completed, week })
const TODAY = '2026-11-06'

test("today's session beats a recent catch-up", () => {
  assert.equal(nextSession([s(1, '2026-11-05'), s(2, TODAY)], TODAY).id, 2)
})

test('a recent miss is offered as a catch-up', () => {
  assert.equal(nextSession([s(1, '2026-11-04'), s(2, '2026-11-08')], TODAY).id, 1)
})

test('an old miss does not block upcoming sessions', () => {
  const sessions = [s(1, '2026-10-08'), s(2, '2026-11-02', true), s(3, '2026-11-08')]
  assert.equal(nextSession(sessions, TODAY).id, 3)
  assert.equal(isMissed(sessions[0], TODAY), true)
})

test('with only old misses left, the latest is offered', () => {
  assert.equal(nextSession([s(1, '2026-10-01'), s(2, '2026-10-08')], TODAY).id, 2)
})

test('a finished plan has no next session', () => {
  assert.equal(nextSession([s(1, '2026-11-01', true)], TODAY), null)
})

test('completed sessions are never missed', () => {
  assert.equal(isMissed(s(1, '2026-10-01', true), TODAY), false)
})

test('current week follows the calendar and stays inside the plan', () => {
  const sessions = [s(1, '2026-10-05', false, 1), s(2, '2026-11-23', false, 8)]
  assert.equal(currentWeek(sessions, '2026-10-05', '2026-10-05'), 1)
  assert.equal(currentWeek(sessions, '2026-10-05', '2026-10-12'), 2)
  assert.equal(currentWeek(sessions, '2026-10-05', TODAY), 5)
  assert.equal(currentWeek(sessions, '2026-10-05', '2027-06-01'), 8)
  assert.equal(currentWeek([], '2026-10-05', TODAY), null)
})
