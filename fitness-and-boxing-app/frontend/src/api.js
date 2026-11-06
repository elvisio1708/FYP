// Thin wrapper around fetch for the Flask API. Throws Error objects that carry
// `status` and `fields` (per-field validation messages) so forms can show them.
async function request(method, path, body) {
  let res
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
      body: body !== undefined ? JSON.stringify(body) : undefined,
      credentials: 'same-origin',
    })
  } catch {
    const err = new Error("Can't reach the server. Check your connection and try again.")
    err.status = 0
    err.fields = {}
    throw err
  }
  let data = null
  try {
    data = await res.json()
  } catch {
    /* non-JSON response */
  }
  if (!res.ok) {
    const err = new Error(data?.error || `Request failed (${res.status})`)
    err.status = res.status
    err.fields = data?.fields || {}
    throw err
  }
  return data
}

export const api = {
  me: () => request('GET', '/me'),
  register: (b) => request('POST', '/register', b),
  login: (b) => request('POST', '/login', b),
  logout: () => request('POST', '/logout', {}),
  changePassword: (b) => request('PUT', '/account/password', b),
  deleteAccount: (b) => request('DELETE', '/account', b),
  profile: () => request('GET', '/profile'),
  saveProfile: (b) => request('PUT', '/profile', b),
  plans: () => request('GET', '/plans'),
  currentPlan: () => request('GET', '/plans/current'),
  createPlan: () => request('POST', '/plans', {}),
  completeSession: (id, b) => request('POST', `/sessions/${id}/complete`, b),
  undoSession: (id) => request('DELETE', `/sessions/${id}/complete`),
  swapExercise: (id) => request('POST', `/exercises/${id}/swap`, {}),
  stats: () => request('GET', '/stats'),
  progress: () => request('GET', '/progress'),
  addProgress: (b) => request('POST', '/progress', b),
  deleteProgress: (id) => request('DELETE', `/progress/${id}`),
}
