/**
 * ChatWidget가 기대하는 authService 인터페이스 (최소 구현)
 * 프로젝트에 authService가 없으면 이 파일을 src/services/authService.js 로 복사 후
 * getUserSync() 반환값만 실제 로그인 사용자에 맞게 수정.
 *
 * 필수:
 * - getUserSync() => { username?: string } | null  (로그인 시 username, 없으면 null)
 * - subscribe(handler) => unsubscribe 함수
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

// 로그인/로그아웃 시 호출해서 상태 갱신 (실제 앱에서는 로그인 성공/실패 시 호출)
export function setAuthUser(user) {
  currentUser = user ? { username: user.username || user.email || 'user', ...user } : null
  subscribers.forEach((fn) => {
    try { fn(getAuthSnapshot()) } catch (e) { /* ignore */ }
  })
}
