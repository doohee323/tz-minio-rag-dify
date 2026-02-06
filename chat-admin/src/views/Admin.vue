<template>
  <div class="admin-page-wrap">
    <div class="admin-page">
    <div class="admin-header">
      <h1>채팅 조회</h1>
    </div>
    <div class="filters-card">
    <div class="filters">
      <label>System <input v-model="filters.systemId" placeholder="e.g. cointutor" /></label>
      <label>User <input v-model="filters.userId" placeholder="e.g. 12345" /></label>
      <label>From <input v-model="filters.fromDate" type="date" /></label>
      <label>To <input v-model="filters.toDate" type="date" /></label>
      <button class="btn-search" @click="doSearch">검색</button>
      <button v-if="conversations.length > 0" class="btn-select" @click="toggleSelectAll">{{ allSelected ? '선택 해제' : '전체 선택' }}</button>
      <button v-if="selectedIds.size > 0" class="btn-delete" @click="deleteSelected" :disabled="deleting">{{ deleting ? '삭제 중...' : '선택 삭제 (' + selectedIds.size + ')' }}</button>
    </div>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="conv-table-wrap">
    <table class="conv-table">
      <thead>
        <tr>
          <th class="col-check"><input type="checkbox" :checked="allSelected" @change="toggleSelectAll" /></th>
          <th>System</th>
          <th>User</th>
          <th>Name</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="c in conversations"
          :key="c.conversation_id"
          :class="{ 'row-selected': isSelected(c) }"
          class="row-click"
          @click="loadMessages(c)"
        >
          <td class="col-check" @click.stop>
            <input type="checkbox" :checked="isSelected(c)" @change="toggleSelect(c)" />
          </td>
          <td>{{ c.system_id }}</td>
          <td>{{ c.user_id }}</td>
          <td>{{ c.name || '-' }}</td>
          <td>{{ formatDate(c.created_at) }}</td>
        </tr>
      </tbody>
    </table>
    </div>
    <p v-if="!loading && !hasSearched" class="empty">검색 조건을 입력한 후 검색하세요.</p>
    <p v-else-if="!loading && conversations.length === 0" class="empty">조건에 맞는 대화가 없습니다.</p>
    <div v-if="selectedConv" class="messages-card">
    <div class="messages-box">
      <h3>Messages: {{ selectedConv.name || selectedConv.conversation_id }}</h3>
      <div v-for="m in messages" :key="m.message_id" :class="['message', 'msg-' + m.role]">
        <strong>{{ m.role === 'user' ? 'User' : 'Bot' }}</strong> {{ formatDate(m.created_at) }}<br>
        {{ m.content }}
      </div>
    </div>
    </div>
    </div>
  </div>
</template>

<script>
const TOKEN_KEY = 'admin_token'

export default {
  name: 'Admin',
  data() {
    return {
      conversations: [],
      messages: [],
      selectedConv: null,
      selectedIds: new Set(),
      filters: { systemId: '', userId: '', fromDate: '', toDate: '' },
      loading: false,
      deleting: false,
      error: '',
      hasSearched: false
    }
  },
  computed: {
    allSelected() {
      return this.conversations.length > 0 && this.selectedIds.size === this.conversations.length
    }
  },
  mounted() {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      this.$router.replace('/login')
      return
    }
  },
  methods: {
    authHeaders() {
      const token = localStorage.getItem(TOKEN_KEY)
      return token ? { 'Authorization': 'Bearer ' + token } : {}
    },
    async doSearch() {
      this.error = ''
      this.loading = true
      const params = new URLSearchParams()
      const sys = this.filters.systemId.trim()
      const usr = this.filters.userId.trim()
      if (sys) params.set('system_id', sys)
      if (usr) params.set('user_id', usr)
      if (this.filters.fromDate) params.set('from_date', this.filters.fromDate)
      if (this.filters.toDate) params.set('to_date', this.filters.toDate)
      try {
        const r = await fetch('/v1/admin/conversations?' + params.toString(), { headers: this.authHeaders() })
        if (r.status === 401) {
          localStorage.removeItem(TOKEN_KEY)
          this.$router.replace('/login')
          return
        }
        if (!r.ok) throw new Error(await r.text())
        this.conversations = await r.json()
        this.selectedConv = null
        this.selectedIds = new Set()
        this.messages = []
        this.hasSearched = true
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
    async loadMessages(c) {
      this.error = ''
      try {
        const url = '/v1/admin/conversations/' + encodeURIComponent(c.conversation_id) + '/messages?system_id=' + encodeURIComponent(c.system_id) + '&user_id=' + encodeURIComponent(c.user_id)
        const r = await fetch(url, { headers: this.authHeaders() })
        if (r.status === 401) {
          localStorage.removeItem(TOKEN_KEY)
          this.$router.replace('/login')
          return
        }
        if (!r.ok) throw new Error('Failed to load messages')
        this.messages = await r.json()
        this.selectedConv = c
      } catch (e) {
        this.error = e.message
      }
    },
    _convKey(c) {
      return c.conversation_id + '|' + c.system_id + '|' + c.user_id
    },
    isSelected(c) {
      return this.selectedIds.has(this._convKey(c))
    },
    toggleSelect(c) {
      const k = this._convKey(c)
      if (this.selectedIds.has(k)) {
        this.selectedIds.delete(k)
      } else {
        this.selectedIds.add(k)
      }
      this.selectedIds = new Set(this.selectedIds)
    },
    toggleSelectAll() {
      if (this.allSelected) {
        this.selectedIds = new Set()
      } else {
        this.selectedIds = new Set(this.conversations.map(c => this._convKey(c)))
      }
    },
    async deleteSelected() {
      if (this.selectedIds.size === 0) return
      this.error = ''
      this.deleting = true
      const toDelete = this.conversations.filter(c => this.selectedIds.has(this._convKey(c)))
      let failed = 0
      for (const c of toDelete) {
        try {
          const r = await fetch(
            '/v1/admin/conversations/' + encodeURIComponent(c.conversation_id) + '?system_id=' + encodeURIComponent(c.system_id) + '&user_id=' + encodeURIComponent(c.user_id),
            { method: 'DELETE', headers: this.authHeaders() }
          )
          if (r.status === 401) {
            localStorage.removeItem(TOKEN_KEY)
            this.$router.replace('/login')
            return
          }
          if (!r.ok) {
            const text = await r.text()
            try { const j = JSON.parse(text); this.error = (j.detail || text).toString() } catch (_) { this.error = text }
            failed++
          } else {
            this.selectedIds.delete(this._convKey(c))
          }
        } catch (e) {
          this.error = e.message
          failed++
        }
      }
      this.selectedIds = new Set(this.selectedIds)
      this.deleting = false
      if (failed === 0) {
        await this.doSearch()
      }
    },
    formatDate(iso) {
      if (!iso) return '-'
      try {
        const d = new Date(iso)
        return isNaN(d.getTime()) ? iso : d.toLocaleString()
      } catch (_) { return iso }
    },
  }
}
</script>

<style scoped>
/* tz-cointutor style */
.admin-page-wrap {
  --primary: #6366f1;
  --secondary: #8b5cf6;
  --dark: #0f172a;
  --dark-light: #1e293b;
  --border: rgba(255, 255, 255, 0.1);
  --border-20: rgba(255, 255, 255, 0.2);
  background: linear-gradient(to bottom right, var(--dark), var(--dark-light), var(--dark));
  min-height: calc(100vh - 56px);
  color: #fff;
}
.admin-page { padding: 1.5rem 1rem; max-width: 80rem; margin: 0 auto; }
.admin-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
.admin-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; }
.filters-card { background: linear-gradient(to bottom right, var(--dark-light), var(--dark)); border: 1px solid var(--border); border-radius: 1rem; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); }
.filters { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.filters label { display: flex; align-items: center; gap: 0.25rem; font-size: 0.875rem; color: #d1d5db; }
.filters input { padding: 0.5rem 0.75rem; border: 1px solid var(--border-20); border-radius: 0.5rem; background: var(--dark); color: #f1f5f9; }
.filters input[type="date"]::-webkit-calendar-picker-indicator { filter: invert(1); cursor: pointer; }
.filters input:focus { outline: none; border-color: var(--primary); }
.btn-search { padding: 0.5rem 1rem; background: linear-gradient(to right, var(--primary), var(--secondary)); color: #fff; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 600; }
.btn-search:hover { box-shadow: 0 10px 20px rgba(99, 102, 241, 0.4); }
.btn-select { padding: 0.5rem 1rem; background: rgba(15, 23, 42, 0.6); color: #9ca3af; border: 1px solid var(--border-20); border-radius: 0.75rem; cursor: pointer; }
.btn-select:hover { background: rgba(30, 41, 59, 0.8); color: #fff; }
.btn-delete { padding: 0.5rem 1rem; background: rgba(239, 68, 68, 0.2); color: #f87171; border: none; border-radius: 0.75rem; cursor: pointer; }
.btn-delete:hover:not(:disabled) { background: rgba(239, 68, 68, 0.3); }
.btn-delete:disabled { opacity: 0.6; cursor: not-allowed; }
.conv-table-wrap { background: linear-gradient(to bottom right, var(--dark-light), var(--dark)); border: 1px solid var(--border); border-radius: 1rem; overflow: hidden; margin-bottom: 1rem; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); }
.col-check { width: 2.5rem; text-align: center; }
.row-selected { background: rgba(99, 102, 241, 0.2); }
.conv-table { border-collapse: collapse; width: 100%; }
.conv-table th, .conv-table td { padding: 0.75rem 1rem; text-align: left; }
.conv-table thead { background: rgba(15, 23, 42, 0.5); }
.conv-table th { font-size: 0.875rem; font-weight: 600; color: #d1d5db; }
.conv-table tbody tr { border-top: 1px solid var(--border); transition: background 0.2s; }
.row-click { cursor: pointer; }
.row-click:hover { background: rgba(15, 23, 42, 0.5); }
.error { color: #f87171; font-size: 0.9rem; }
.empty { color: #9ca3af; padding: 2rem; text-align: center; }
.messages-card { background: linear-gradient(to bottom right, var(--dark-light), var(--dark)); border: 1px solid var(--border); border-radius: 1rem; padding: 1.5rem; margin-top: 1rem; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); }
.messages-box h3 { margin: 0 0 1rem; font-size: 1rem; font-weight: 600; }
.message { padding: 0.75rem; margin-bottom: 0.5rem; border-radius: 0.5rem; white-space: pre-wrap; }
.msg-user { background: rgba(99, 102, 241, 0.15); border-left: 3px solid var(--primary); }
.msg-assistant { background: rgba(139, 92, 246, 0.15); border-left: 3px solid var(--secondary); }
</style>
