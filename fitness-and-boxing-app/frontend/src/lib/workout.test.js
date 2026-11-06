import assert from 'node:assert/strict'
import { test } from 'node:test'
import { buildSteps, stepLabel, totalSeconds } from './workout.js'

const warm = { name: 'Jog', kind: 'warmup', sets: 1, duration_seconds: 180, rest_seconds: 0 }
const cool = { name: 'Stretch', kind: 'cooldown', sets: 1, duration_seconds: 300, rest_seconds: 0 }
const box = (name, sets) => ({ name, kind: 'boxing', sets, duration_seconds: 180, rest_seconds: 60 })
const station = (name) => ({ ...box(`Circuit: ${name}`, 2), duration_seconds: 30, rest_seconds: 15, circuit: true })
const titles = (steps) => steps.map((s) => s.title)

test('rounds alternate with rest and number across the whole session', () => {
  const steps = buildSteps([box('Shadow', 2), box('Bag', 1)])
  assert.deepEqual(titles(steps), ['Shadow', 'Rest', 'Shadow', 'Rest', 'Bag'])
  assert.deepEqual(steps.filter((s) => s.round).map((s) => s.round), [1, 2, 3])
  assert.equal(stepLabel(steps[4]), 'Round 3 of 3')
})

test('no rest is added between the last round and the cool-down', () => {
  const steps = buildSteps([warm, box('Shadow', 1), cool])
  assert.deepEqual(titles(steps), ['Jog', 'Shadow', 'Stretch'])
  assert.equal(steps[0].phase, 'warmup')
  assert.equal(steps[2].phase, 'cooldown')
})

test('circuits loop through every station before repeating', () => {
  const steps = buildSteps([station('Skipping'), station('Burpees'), cool])
  assert.deepEqual(titles(steps), [
    'Skipping', 'Rest', 'Burpees', 'Rest', 'Skipping', 'Rest', 'Burpees', 'Stretch',
  ])
  assert.equal(stepLabel(steps[4]), 'Round 2 of 2 · Station 1 of 2')
})

test('rep-based sets wait for the user and rest between sets', () => {
  const gym = { name: 'Squat', kind: 'gym', sets: 2, reps: 8, rest_seconds: 90, notes: 'Brace' }
  const steps = buildSteps([gym])
  assert.equal(steps[0].seconds, null)
  assert.equal(steps[0].reps, 8)
  assert.equal(steps[1].seconds, 90)
  assert.equal(stepLabel(steps[2]), 'Set 2 of 2')
  assert.equal(totalSeconds(steps), 8 * 4 * 2 + 90)
})

test('rest steps point at what comes next', () => {
  const steps = buildSteps([box('Shadow', 1), box('Bag', 1)])
  assert.equal(steps[1].next, 'Bag')
  assert.equal(steps[2].next, null)
})

test('an empty session has no steps', () => {
  assert.deepEqual(buildSteps([]), [])
})
