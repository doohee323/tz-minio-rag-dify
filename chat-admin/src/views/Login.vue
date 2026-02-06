<template>
  <div class="login-page">
    <div class="login-card">
      <h1>로그인</h1>
      <p class="subtitle">채팅 관리 페이지에 로그인합니다.</p>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="username">사용자명</label>
          <input
            id="username"
            v-model="username"
            type="text"
            class="form-input"
            placeholder="사용자명"
            required
          >
        </div>
        <div class="form-group">
          <label for="password">비밀번호</label>
          <input
            id="password"
            v-model="password"
            type="password"
            class="form-input"
            placeholder="비밀번호"
            required
          >
        </div>
        <p v-if="error" class="error-msg">{{ error }}</p>
        <button type="submit" class="btn-submit" :disabled="loading">
          {{ loading ? '로그인 중...' : '로그인' }}
        </button>
      </form>

      <p class="footer-note">
        <router-link to="/register">회원가입</router-link>
      </p>
    </div>
  </div>
</template>

<script>
const TOKEN_KEY = 'admin_token'

export default {
  name: 'Login',
  data() {
    return {
      username: '',
      password: '',
      loading: false,
      error: ''
    }
  },
  methods: {
    async handleLogin() {
      this.error = ''
      this.loading = true
      try {
        const r = await fetch('/v1/admin/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: this.username.trim(),
            password: this.password
          })
        })
        if (!r.ok) {
          const data = await r.json().catch(() => ({}))
          throw new Error(data.detail || '로그인 실패')
        }
        const data = await r.json()
        const token = data.access_token
        if (!token) throw new Error('토큰을 받지 못했습니다.')
        localStorage.setItem(TOKEN_KEY, token)
        this.$router.replace('/admin')
      } catch (e) {
        this.error = e.message || '로그인에 실패했습니다.'
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.login-page {
  min-height: calc(100vh - 56px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: var(--bg, #0f172a);
  color: #f1f5f9;
}
.login-card {
  width: 100%;
  max-width: 400px;
  background: var(--surface, #1e293b);
  border-radius: 12px;
  padding: 2rem;
  border: 1px solid rgba(255,255,255,0.06);
}
.login-card h1 { font-size: 1.5rem; margin: 0 0 0.5rem; color: #f1f5f9; }
.subtitle { color: #94a3b8; font-size: 0.9rem; margin-bottom: 1.5rem; }
.login-form { display: flex; flex-direction: column; gap: 1.25rem; }
.form-group { display: flex; flex-direction: column; gap: 0.4rem; }
.form-group label { font-size: 0.85rem; font-weight: 600; color: #94a3b8; }
.form-input {
  padding: 0.6rem 0.9rem;
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 8px;
  background: #0f172a;
  color: #f1f5f9;
  font-size: 1rem;
}
.form-input:focus { outline: none; border-color: #38bdf8; }
.error-msg { color: #f87171; font-size: 0.9rem; margin: 0; }
.btn-submit {
  padding: 0.75rem 1rem;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
}
.btn-submit:hover:not(:disabled) { background: #1d4ed8; }
.btn-submit:disabled { opacity: 0.6; cursor: not-allowed; }
.footer-note {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255,255,255,0.06);
  font-size: 0.9rem;
  color: #94a3b8;
}
.footer-note a { color: #38bdf8; }
.footer-note a:hover { text-decoration: underline; }
</style>
