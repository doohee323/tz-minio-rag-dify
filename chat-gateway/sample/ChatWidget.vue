<template>
  <div class="chat-widget" v-if="chatGatewayUrl && apiKey">
    <transition name="chat-panel">
      <div v-show="open" class="chat-widget-panel chat-widget-panel--open">
        <div class="chat-widget-header">
          <span>{{ chatT.title }}</span>
          <button type="button" class="chat-widget-close" @click="open = false" :aria-label="chatT.close">&times;</button>
        </div>
        <div class="chat-widget-body">
          <iframe
            v-if="iframeSrc"
            :src="iframeSrc"
            class="chat-widget-iframe"
            :title="chatT.title"
          />
          <div v-else-if="loadError" class="chat-widget-no-token">
            <p>{{ chatT.tokenError }}</p>
            <p class="small">{{ loadError }}</p>
          </div>
          <div v-else class="chat-widget-no-token">
            <p>{{ chatT.loading }}</p>
          </div>
        </div>
      </div>
    </transition>
    <button
      v-show="!open"
      type="button"
      class="chat-widget-toggle"
      @click="toggleOpen"
      :title="chatT.open"
      :aria-label="chatT.title"
    >
      <span>💬</span>
    </button>
  </div>
</template>

<script>
// 채팅은 chat-gateway가 처리. 토큰·다국어(ui) 모두 API에서 받음.
// .env: VUE_APP_CHAT_GATEWAY_URL, VUE_APP_CHAT_GATEWAY_API_KEY
// user_id: 로그인 시 username, 비로그인 시 'anonymous'
import authService from '@/services/authService'

export default {
  name: 'ChatWidget',
  data() {
    const base = (process.env.VUE_APP_CHAT_GATEWAY_URL || 'http://localhost:8088').replace(/\/$/, '')
    const apiKey = (process.env.VUE_APP_CHAT_GATEWAY_API_KEY || '').trim()
    return {
      open: false,
      chatGatewayUrl: base,
      apiKey,
      systemId: (process.env.VUE_APP_CHAT_GATEWAY_SYSTEM_ID || 'drillquiz').trim(),
      chatToken: null,
      chatUi: null,
      loadError: null,
      unsubscribeAuth: null
    }
  },
  computed: {
    chatT() {
      return this.chatUi || {
        title: 'Chat',
        close: 'Close',
        open: 'Open chat',
        tokenError: 'Could not load chat token.',
        loading: 'Loading...'
      }
    },
    chatLang() {
      const locale = (this.$i18n && this.$i18n.locale) ? this.$i18n.locale : 'en'
      const allowed = ['en', 'es', 'ko', 'zh', 'ja']
      return allowed.includes(locale) ? locale : 'en'
    },
    iframeSrc() {
      if (!this.chatToken) return ''
      return `${this.chatGatewayUrl}/chat?token=${encodeURIComponent(this.chatToken)}&embed=1&lang=${encodeURIComponent(this.chatLang)}`
    }
  },
  mounted() {
    this.unsubscribeAuth = authService.subscribe(() => {
      this.chatToken = null
      this.chatUi = null
    })
  },
  beforeUnmount() {
    if (this.unsubscribeAuth) this.unsubscribeAuth()
  },
  methods: {
    getChatUserId() {
      const user = authService.getUserSync()
      return (user && user.username) ? String(user.username) : 'anonymous'
    },
    async fetchToken() {
      if (this.chatToken) return
      this.loadError = null
      const userId = this.getChatUserId()
      const lang = this.chatLang
      try {
        const url = `${this.chatGatewayUrl}/v1/chat-token?system_id=${encodeURIComponent(this.systemId)}&user_id=${encodeURIComponent(userId)}&lang=${encodeURIComponent(lang)}`
        const res = await fetch(url, { headers: { 'X-API-Key': this.apiKey } })
        if (!res.ok) {
          const text = await res.text()
          throw new Error(text || `HTTP ${res.status}`)
        }
        const data = await res.json()
        this.chatToken = data.token || null
        if (!this.chatToken) throw new Error('No token in response')
        this.chatUi = data.ui || null
      } catch (e) {
        this.loadError = e.message || 'Unknown error'
      }
    },
    toggleOpen() {
      this.open = !this.open
      if (this.open && !this.chatToken && !this.loadError) this.fetchToken()
    }
  }
}
</script>

<style scoped>
.chat-widget {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 1040;
  font-family: system-ui, sans-serif;
}

.chat-widget-panel {
  position: absolute;
  right: 0;
  width: 380px;
  max-width: calc(100vw - 40px);
  height: 520px;
  max-height: calc(100vh - 120px);
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 패널 열렸을 때: 버튼이 숨겨지므로 하단까지 내림 (버튼 높이만큼 여백 제거) */
.chat-widget-panel--open {
  bottom: 20px;
  max-height: calc(100vh - 40px);
}

.chat-widget-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #1a1a2e;
  color: #eee;
  font-size: 0.95rem;
  font-weight: 500;
}

.chat-widget-close {
  background: none;
  border: none;
  color: #eee;
  font-size: 1.4rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 4px;
  opacity: 0.9;
}

.chat-widget-close:hover {
  opacity: 1;
}

.chat-widget-body {
  flex: 1;
  min-height: 0;
}

.chat-widget-iframe {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
}

.chat-widget-no-token {
  padding: 1.5rem;
  text-align: center;
  color: #6c757d;
  font-size: 0.9rem;
}

.chat-widget-no-token .small {
  font-size: 0.8rem;
  margin-top: 0.5rem;
}

.chat-widget-toggle {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: #2563eb;
  color: #fff;
  border: none;
  box-shadow: 0 2px 12px rgba(37, 99, 235, 0.4);
  cursor: pointer;
  font-size: 1.5rem;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.chat-widget-toggle:hover {
  background: #1d4ed8;
}

.chat-panel-enter-active,
.chat-panel-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.chat-panel-enter-from,
.chat-panel-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
