<template>
  <div id="app">
    <header class="app-header">
      <div class="nav-left">
        <router-link to="/" class="logo">TZ-Chat Gateway</router-link>
        <template v-if="isAdminArea">
          <router-link to="/admin/systems" class="nav-link">채팅관리</router-link>
          <router-link to="/admin" class="nav-link">채팅조회</router-link>
        </template>
      </div>
      <nav class="nav-right">
        <template v-if="isAdminArea">
          <button type="button" class="btn-logout" @click="logout">로그아웃</button>
        </template>
        <template v-else>
          <router-link to="/register" class="nav-link">회원가입</router-link>
          <router-link to="/login" class="nav-link">로그인</router-link>
        </template>
      </nav>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script>
const TOKEN_KEY = 'admin_token'

export default {
  name: 'App',
  computed: {
    isAdminArea() {
      return this.$route.path.startsWith('/admin')
    }
  },
  methods: {
    logout() {
      localStorage.removeItem(TOKEN_KEY)
      this.$router.replace('/login')
    }
  }
}
</script>

<style>
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, sans-serif; background: #0f172a; }
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: var(--bg, #0f172a);
  border-bottom: 1px solid rgba(255,255,255,0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  z-index: 100;
}
.app-header .logo {
  font-size: 1.1rem;
  font-weight: 700;
  color: #f1f5f9;
  text-decoration: none;
}
.app-header .logo:hover { color: #38bdf8; }
.nav-left { display: flex; align-items: center; gap: 1rem; }
.nav-right { display: flex; align-items: center; gap: 1rem; }
.nav-link {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.95rem;
  padding: 0.4rem 0.75rem;
  border-radius: 8px;
  border: 1px solid rgba(56, 189, 248, 0.25);
}
.nav-link:hover { color: #38bdf8; background: rgba(56, 189, 248, 0.1); }
.btn-logout { padding: 0.4rem 0.75rem; background: rgba(100, 116, 139, 0.3); color: #94a3b8; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; cursor: pointer; font-size: 0.95rem; }
.btn-logout:hover { background: rgba(100, 116, 139, 0.5); color: #fff; }
.app-main { padding-top: 56px; min-height: 100vh; background: #0f172a; }
</style>
