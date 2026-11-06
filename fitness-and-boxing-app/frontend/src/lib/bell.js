// Ring sounds, synthesised so there are no audio files to ship. The context has
// to be created from a user gesture, hence unlock() on the Start button.
let ctx = null
let muted = false

export function unlock() {
  const Ctx = window.AudioContext || window.webkitAudioContext
  if (!Ctx) return
  ctx ??= new Ctx()
  ctx.resume?.()
}

export const setMuted = (value) => { muted = value }

// A bell is a few inharmonic partials decaying at different speeds.
function strike(at, volume = 0.5) {
  for (const [ratio, gain, decay] of [[1, 1, 1.5], [2.76, 0.5, 0.9], [5.4, 0.25, 0.5]]) {
    const osc = ctx.createOscillator()
    const env = ctx.createGain()
    osc.frequency.value = 830 * ratio
    env.gain.setValueAtTime(volume * gain, at)
    env.gain.exponentialRampToValueAtTime(0.0001, at + decay)
    osc.connect(env).connect(ctx.destination)
    osc.start(at)
    osc.stop(at + decay)
  }
}

function play(times, volume) {
  if (!ctx || muted) return
  times.forEach((offset) => strike(ctx.currentTime + offset, volume))
}

export const roundStart = () => play([0], 0.5)
export const roundEnd = () => play([0, 0.28, 0.56], 0.5)
export const tenSeconds = () => play([0, 0.14], 0.22) // the clapper before the bell
export const tick = () => play([0], 0.1)
