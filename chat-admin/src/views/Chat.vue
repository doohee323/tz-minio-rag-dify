<template>
  <div class="chat-page" :class="{ 'chat-page--modal': inModal }" v-if="init">
    <div class="header" v-if="!init.embed">
      <span>System: {{ init.systemId }} · User: {{ init.userId }}</span>
    </div>
    <div class="layout" :class="{ 'layout--embed': init.embed }">
      <aside class="sidebar" v-if="!init.embed">
        <h3>Conversations</h3>
        <button type="button" class="btn btn-primary" @click="newConversation">{{ t.sendNew }}</button>
        <ul class="conv-list">
          <li
            v-for="c in conversations"
            :key="c.id"
            :class="{ active: c.id === currentConversationId }"
            @click="selectConversation(c.id)"
          >
            <span class="conv-name">{{ c.name || c.id || '(Conversation)' }}</span>
            <button type="button" class="btn-del-conv" @click.stop="deleteConversation(c.id)" title="삭제">×</button>
          </li>
        </ul>
      </aside>
      <main class="main">
        <div class="messages" ref="messages">
          <p class="empty-state" v-show="messages.length === 0">{{ emptyText }}</p>
          <div
            v-for="(m, i) in messages"
            :key="i"
            :class="['msg', 'msg-' + m.role]"
          >
            <div class="msg-role">{{ m.role === 'user' ? t.me : t.bot }}</div>
            <div v-html="escapeHtml(m.content)"></div>
          </div>
        </div>
        <div class="error">{{ error }}</div>
        <div class="input-row">
          <input
            type="text"
            v-model="inputText"
            :placeholder="t.placeholder"
            autocomplete="off"
            @keydown.enter.prevent="sendMessage"
          >
          <button type="button" class="btn btn-primary" @click="sendMessage">{{ t.send }}</button>
        </div>
      </main>
    </div>
  </div>
  <div v-else class="chat-page chat-page--no-init">
    <p>Token is required. Add <code>?token=&lt;JWT&gt;</code> to the URL, or get a token via <code>GET /v1/chat-token</code>.</p>
    <p><router-link to="/">← Back to intro</router-link></p>
  </div>
</template>

<script>
const ALLOWED_LANGS = ['en', 'es', 'ko', 'zh', 'ja']
const UI = {
  en: {
    placeholder: 'Type a message...',
    send: 'Send',
    sendNew: 'New conversation',
    empty: 'Type a message.',
    emptyFull: 'Start a new chat or select one from the list.',
    me: 'Me',
    bot: 'Bot',
    errorList: 'Failed to load conversations.',
    errorMessages: 'Failed to load messages.',
    errorSend: 'Send failed.'
  },
  es: {
    placeholder: 'Escribe un mensaje...',
    send: 'Enviar',
    sendNew: 'Nueva conversación',
    empty: 'Escribe un mensaje.',
    emptyFull: 'Inicia un chat nuevo o elige uno de la lista.',
    me: 'Yo',
    bot: 'Bot',
    errorList: 'Error al cargar conversaciones.',
    errorMessages: 'Error al cargar mensajes.',
    errorSend: 'Error al enviar.'
  },
  ko: {
    placeholder: '메시지를 입력하세요...',
    send: '전송',
    sendNew: '새 대화',
    empty: '메시지를 입력하세요.',
    emptyFull: '새 대화를 시작하거나 왼쪽에서 대화를 선택하세요.',
    me: '나',
    bot: '봇',
    errorList: '대화 목록 조회 실패.',
    errorMessages: '메시지 조회 실패.',
    errorSend: '전송 실패.'
  },
  zh: {
    placeholder: '输入消息...',
    send: '发送',
    sendNew: '新对话',
    empty: '输入消息。',
    emptyFull: '开始新对话或从列表中选择。',
    me: '我',
    bot: '助手',
    errorList: '加载对话列表失败。',
    errorMessages: '加载消息失败。',
    errorSend: '发送失败。'
  },
  ja: {
    placeholder: 'メッセージを入力...',
    send: '送信',
    sendNew: '新しい会話',
    empty: 'メッセージを入力してください。',
    emptyFull: '新しい会話を始めるか、一覧から選択してください。',
    me: '自分',
    bot: 'ボット',
    errorList: '会話一覧の取得に失敗しました。',
    errorMessages: 'メッセージの取得に失敗しました。',
    errorSend: '送信に失敗しました。'
  }
}

function resolveLang(langParam) {
  if (langParam && ALLOWED_LANGS.includes(langParam)) return langParam
  const nav = (navigator.language || navigator.userLanguage || '').toLowerCase()
  if (nav.startsWith('ko')) return 'ko'
  if (nav.startsWith('ja')) return 'ja'
  if (nav.startsWith('zh')) return 'zh'
  if (nav.startsWith('es')) return 'es'
  return 'en'
}

export default {
  name: 'Chat',
  props: {
    chatToken: { type: String, default: '' },
    chatSystemId: { type: String, default: '' },
    chatUserId: { type: String, default: '' },
    inModal: { type: Boolean, default: false }
  },
  data() {
    const lang = resolveLang(null)
    return {
      lang,
      t: UI[lang] || UI.en,
      conversations: [],
      currentConversationId: null,
      messages: [],
      inputText: '',
      error: ''
    }
  },
  computed: {
    init() {
      if (this.chatToken && this.chatSystemId && this.chatUserId) {
        return {
          token: this.chatToken,
          systemId: this.chatSystemId,
          userId: this.chatUserId,
          embed: false,
          lang: ''
        }
      }
      let raw = (typeof window !== 'undefined' && window.__CHAT_INIT__) || {}
      if (!raw.token && typeof window !== 'undefined') {
        const params = new URLSearchParams(window.location.search)
        const token = params.get('token')
        const embed = params.get('embed') === '1'
        const langParam = params.get('lang') || ''
        if (token) {
          try {
            const payload = JSON.parse(atob(token.split('.')[1]))
            raw = { token, systemId: payload.system_id || '', userId: payload.user_id || '', embed, lang: langParam }
          } catch (_) {
            raw = {}
          }
        }
      }
      return (raw.token && raw.systemId !== undefined && raw.userId !== undefined) ? raw : null
    },
    emptyText() {
      return this.init && this.init.embed ? this.t.empty : this.t.emptyFull
    }
  },
  mounted() {
    if (this.init && !this.init.embed) {
      this.loadConversations()
    }
  },
  updated() {
    this.$nextTick(() => {
      const el = this.$refs.messages
      if (el) el.scrollTop = el.scrollHeight
    })
  },
  methods: {
    authHeader() {
      return {
        'Authorization': 'Bearer ' + this.init.token,
        'Content-Type': 'application/json'
      }
    },
    escapeHtml(s) {
      if (s == null) return ''
      const div = document.createElement('div')
      div.textContent = s
      return div.innerHTML
    },
    newConversation() {
      this.currentConversationId = null
      this.messages = []
      this.error = ''
    },
    async loadConversations() {
      if (!this.init || this.init.embed) return
      try {
        const r = await fetch(
          '/v1/conversations?system_id=' + encodeURIComponent(this.init.systemId) + '&user_id=' + encodeURIComponent(this.init.userId),
          { headers: this.authHeader() }
        )
        if (!r.ok) throw new Error(this.t.errorList)
        this.conversations = await r.json()
      } catch (e) {
        this.error = e.message || this.t.errorList
      }
    },
    async deleteConversation(id) {
      if (!this.init || this.init.embed) return
      try {
        const r = await fetch(
          '/v1/conversations/' + encodeURIComponent(id) + '?system_id=' + encodeURIComponent(this.init.systemId) + '&user_id=' + encodeURIComponent(this.init.userId),
          { method: 'DELETE', headers: this.authHeader() }
        )
        if (!r.ok) {
          const raw = await r.text()
          let err = raw
          try { const j = JSON.parse(raw); if (j.detail) err = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail) } catch (_) {}
          throw new Error(err)
        }
        if (this.currentConversationId === id) {
          this.currentConversationId = null
          this.messages = []
        }
        await this.loadConversations()
      } catch (e) {
        this.error = e.message || '삭제 실패'
      }
    },
    async selectConversation(id) {
      if (!this.init || this.init.embed) return
      this.currentConversationId = id
      this.messages = []
      if (!id) return
      try {
        const r = await fetch(
          '/v1/conversations/' + encodeURIComponent(id) + '/messages?system_id=' + encodeURIComponent(this.init.systemId) + '&user_id=' + encodeURIComponent(this.init.userId),
          { headers: this.authHeader() }
        )
        if (!r.ok) throw new Error(this.t.errorMessages)
        const data = await r.json()
        this.messages = data.map(m => ({ role: m.role, content: m.content }))
      } catch (e) {
        this.error = e.message || this.t.errorMessages
      }
    },
    async sendMessage() {
      const text = this.inputText.trim()
      if (!text || !this.init) return
      this.error = ''
      this.inputText = ''
      this.messages.push({ role: 'user', content: text })
      try {
        const body = { message: text, inputs: { language: this.lang } }
        if (this.currentConversationId) body.conversation_id = this.currentConversationId
        const r = await fetch('/v1/chat', {
          method: 'POST',
          headers: this.authHeader(),
          body: JSON.stringify(body)
        })
        if (!r.ok) {
          const raw = await r.text()
          let errText = raw
          try {
            const j = JSON.parse(raw)
            if (j.detail) errText = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
          } catch (_) {}
          throw new Error(errText || this.t.errorSend)
        }
        const data = await r.json()
        if (data.conversation_id) this.currentConversationId = data.conversation_id
        this.messages.push({ role: 'assistant', content: data.answer || '' })
        if (!this.init.embed) this.loadConversations()
      } catch (e) {
        this.error = e.message || this.t.errorSend
      }
    }
  }
}
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.chat-page--no-init {
  padding: 2rem;
  font-family: system-ui, sans-serif;
}
.layout {
  display: flex;
  flex: 1;
  height: calc(100vh - 40px);
  min-height: 0;
}
.chat-page--modal {
  height: 100%;
  min-height: 400px;
}
.chat-page--modal .layout {
  height: calc(100% - 40px);
}
.layout--embed {
  height: 100vh;
}
.chat-page--modal .layout--embed {
  height: 100%;
}
.header {
  padding: 0.6rem 1rem;
  background: #1a1a2e;
  color: #eee;
  font-size: 0.9rem;
}
.sidebar {
  width: 240px;
  background: #fff;
  border-right: 1px solid #e5e7eb;
  overflow-y: auto;
  padding: 0.5rem;
}
.sidebar h3 {
  margin: 0 0 0.5rem;
  font-size: 0.85rem;
  color: #6b7280;
}
.btn {
  padding: 0.4rem 0.75rem;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  background: #fff;
  cursor: pointer;
  font-size: 0.9rem;
}
.btn:hover { background: #f9fafb; }
.btn-primary {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}
.btn-primary:hover { background: #1d4ed8; }
.conv-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.conv-list li {
  padding: 0.5rem 0.6rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.conv-name { flex: 1; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.btn-del-conv {
  flex-shrink: 0;
  width: 1.5rem;
  height: 1.5rem;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #6b7280;
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  opacity: 0.7;
}
.btn-del-conv:hover {
  background: #fee2e2;
  color: #dc2626;
  opacity: 1;
}
.conv-list li:hover { background: #f3f4f6; }
.conv-list li.active { background: #dbeafe; font-weight: 500; }
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  min-width: 0;
  min-height: 0;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.msg {
  max-width: 85%;
  padding: 0.6rem 0.9rem;
  border-radius: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg-user { align-self: flex-end; background: #2563eb; color: #fff; }
.msg-assistant { align-self: flex-start; background: #f3f4f6; color: #111; }
.msg-role { font-size: 0.75rem; opacity: 0.8; margin-bottom: 0.2rem; }
.input-row {
  padding: 0.75rem 1rem;
  border-top: 1px solid #e5e7eb;
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.input-row input {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 1rem;
}
.input-row input:focus { outline: none; border-color: #2563eb; }
.empty-state { color: #6b7280; text-align: center; padding: 2rem; }
.error { color: #dc2626; font-size: 0.9rem; padding: 0.5rem; }
</style>
