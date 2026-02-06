/**
 * API config for TZ-Chat Gateway frontend (tz-cointutor style)
 * VUE_APP_API_BASE: API base URL for links to /docs, /cache (empty = same origin)
 */
const ENVIRONMENT = process.env.VUE_APP_ENVIRONMENT || 'development'
const API_BASE = process.env.VUE_APP_API_BASE || ''

const apiBase = (typeof window !== 'undefined' && !API_BASE)
  ? window.location.origin
  : API_BASE

export {
  ENVIRONMENT,
  apiBase
}
