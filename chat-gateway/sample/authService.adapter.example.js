/**
 * Minimal authService interface expected by ChatWidget.
 * If your project has no authService, copy this file to src/services/authService.js
 * and adjust getUserSync() return value for your logged-in user.
 *
 * Required:
 * - getUserSync() => { username?: string } | null  (username when logged in, null otherwise)
 * - subscribe(handler) => unsubscribe function
 */
let currentUser = null
const subscribers = new Set()

function getAuthSnapshot() {
  return {
    isAuthenticated: !!currentUser,
    user: currentUser ? { ...currentUser } : null
  }
}

export default {
  getUserSync() {
    return currentUser ? { ...currentUser } : null
  },
  subscribe(handler) {
    if (typeof handler !== 'function') return () => {}
    subscribers.add(handler)
    handler(getAuthSnapshot())
    return () => subscribers.delete(handler)
  }
}

// Call on login/logout to refresh state (in your app, call on login success/failure)
export function setAuthUser(user) {
  currentUser = user ? { username: user.username || user.email || 'user', ...user } : null
  subscribers.forEach((fn) => {
    try { fn(getAuthSnapshot()) } catch (e) { /* ignore */ }
  })
}
