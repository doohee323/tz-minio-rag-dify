<template>
  <div class="register-page">
    <div class="register-card">
      <h1>관리자 회원가입</h1>
      <p class="subtitle">채팅 관리용 계정을 생성합니다.</p>

      <form @submit.prevent="handleRegister" class="register-form">
        <div class="form-group">
          <label for="username">사용자명</label>
          <input
            id="username"
            v-model="username"
            type="text"
            class="form-input"
            placeholder="로그인에 사용할 아이디"
            required
          >
        </div>
        <div class="form-group">
          <label for="name">이름</label>
          <input
            id="name"
            v-model="name"
            type="text"
            class="form-input"
            placeholder="이름"
            required
          >
        </div>
        <div class="form-group">
          <label for="email">이메일</label>
          <input
            id="email"
            v-model="email"
            type="email"
            class="form-input"
            placeholder="your@email.com"
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
            placeholder="비밀번호 (6자 이상)"
            required
            minlength="6"
          >
        </div>
        <div class="form-group">
          <label for="passwordConfirm">비밀번호 확인</label>
          <input
            id="passwordConfirm"
            v-model="passwordConfirm"
            type="password"
            class="form-input"
            placeholder="비밀번호 재입력"
            required
            minlength="6"
          >
        </div>
        <p v-if="error" class="error-msg">{{ error }}</p>
        <button type="submit" class="btn-submit" :disabled="loading">
          {{ loading ? '가입 중...' : '가입' }}
        </button>
      </form>

      <p class="footer-note">
        이미 계정이 있으신가요? <router-link to="/login">로그인</router-link>
      </p>
    </div>
  </div>
</template>

<script>
const TOKEN_KEY = 'admin_token'

export default {
  name: 'Register',
  data() {
    return {
      username: '',
      name: '',
      email: '',
      password: '',
      passwordConfirm: '',
      loading: false,
      error: ''
    }
  },
  methods: {
    async handleRegister() {
      this.error = ''
      if (this.password.length < 6) {
        this.error = '비밀번호는 6자 이상이어야 합니다.'
        return
      }
      if (this.password !== this.passwordConfirm) {
        this.error = '비밀번호가 일치하지 않습니다.'
        return
      }
      this.loading = true
      try {
        const r = await fetch('/v1/admin/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: this.username.trim(),
            name: this.name.trim(),
            email: this.email.trim().toLowerCase(),
            password: this.password,
            password_confirm: this.passwordConfirm
          })
        })
        if (!r.ok) {
          const data = await r.json().catch(() => ({}))
          const detail = Array.isArray(data.detail) ? data.detail[0]?.msg || data.detail : data.detail
          throw new Error(typeof detail === 'string' ? detail : '가입 실패')
        }
        const data = await r.json()
        const token = data.access_token
        if (!token) throw new Error('토큰을 받지 못했습니다.')
        localStorage.setItem(TOKEN_KEY, token)
        this.$router.replace('/admin')
      } catch (e) {
        this.error = e.message || '가입에 실패했습니다.'
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.register-page {
  min-height: calc(100vh - 56px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: var(--bg, #0f172a);
  color: #f1f5f9;
}
.register-card {
  width: 100%;
  max-width: 400px;
  background: var(--surface, #1e293b);
  border-radius: 12px;
  padding: 2rem;
  border: 1px solid rgba(255,255,255,0.06);
}
.register-card h1 { font-size: 1.5rem; margin: 0 0 0.5rem; color: #f1f5f9; }
.subtitle { color: #94a3b8; font-size: 0.9rem; margin-bottom: 1.5rem; }
.register-form { display: flex; flex-direction: column; gap: 1.25rem; }
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
