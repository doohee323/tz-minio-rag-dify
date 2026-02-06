<template>
  <div class="about wrap">
    <h1>TZ-Chat Gateway</h1>
    <p class="tagline">Unified chat API in front of Dify. Part of the tz-chatbot stack.</p>

    <div class="card">
      <h2>What this is</h2>
      <p>
        This service is the <strong>TZ-Chat Gateway</strong>: a single API and chat UI for multiple apps (e.g. DrillQuiz, CoinTutor).
        It sits in front of <a href="https://dify.ai" target="_blank" rel="noopener" class="link">Dify</a>,
        manages users and conversations, and can sync chat history to its own database for support and analytics.
        Sample integration: <a href="https://devops.drillquiz.com/" target="_blank" rel="noopener" class="link">devops.drillquiz.com</a> (DrillQuiz).
      </p>
    </div>

    <div class="card">
      <h2>Project: tz-chatbot</h2>
      <p>
        The full stack runs on Kubernetes: <strong>MinIO</strong> (object store), <strong>Qdrant</strong> (vector DB),
        <strong>RAG backends</strong> (CoinTutor / DrillQuiz), <strong>Dify</strong> (chatbots), and this <strong>TZ-Chat Gateway</strong>.
        RAG ingestion runs on a schedule; Dify apps call the RAG backends as tools.
      </p>
    </div>

    <h2 class="section-title">1. Workflow</h2>
    <p class="tagline-sm">Check out this repo, use sample apps (DrillQuiz / CoinTutor) as reference to register and apply your app.</p>
    <div class="diagram">
      <div class="diagram-title">Flow: add your app, then use chat</div>
      <div class="flow-row">
        <span class="flow-step">1. Check out this code</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step">2. Register your app (reference: DrillQuiz / CoinTutor)</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step">3. Get token &amp; open chat page</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step">4. Chat</span>
      </div>
      <div class="flow-row flow-detail">
        <span class="flow-step">You add and register your app; you do not choose from existing apps. Token: issued after your app's login, or call <code>/v1/chat-token</code> with API Key.</span>
      </div>
    </div>

    <h2 class="section-title">2. How the app operates</h2>
    <p class="tagline-sm">Request-to-response processing order</p>
    <div class="diagram">
      <div class="diagram-title">Request → response sequence</div>
      <div class="seq-row">
        <span class="seq-label">Client</span>
        <span class="seq-box">Send message from chat UI (JWT or API Key)</span>
      </div>
      <div class="arch-arrow-row">↓</div>
      <div class="seq-row">
        <span class="seq-label">TZ-Chat Gateway</span>
        <span class="seq-box">Validate JWT/API Key → sync conversation/messages to DB → proxy to Dify API</span>
      </div>
      <div class="arch-arrow-row">↓</div>
      <div class="seq-row">
        <span class="seq-label">Dify</span>
        <span class="seq-box">Run DrillQuiz or CoinTutor app (calls RAG tool when needed)</span>
      </div>
      <div class="arch-arrow-row">↓</div>
      <div class="seq-row">
        <span class="seq-label">RAG</span>
        <span class="seq-box">Qdrant + RAG Backend search → return results to Dify (required)</span>
      </div>
      <div class="arch-arrow-row">↓</div>
      <div class="seq-row">
        <span class="seq-label">Response</span>
        <span class="seq-box">Dify → TZ-Chat Gateway → client (streaming or normal response)</span>
      </div>
    </div>

    <h2 class="section-title">3. Architecture</h2>
    <p class="tagline-sm">tz-chatbot stack components</p>
    <div class="diagram">
      <div class="diagram-title">Components and relationships</div>
      <div class="arch-arrow-row">Ingress (TLS / routing)</div>
      <div class="arch-arrow-row">↓</div>
      <div class="arch-grid">
        <div class="arch-box entry">TZ-Chat Gateway<br><small>(FastAPI)</small></div>
        <div class="arch-box gw">Dify<br><small>DrillQuiz / CoinTutor</small></div>
        <div class="arch-box app">RAG Backend<br><small>CoinTutor, DrillQuiz</small></div>
        <div class="arch-box data">Qdrant<br><small>vector DB</small></div>
        <div class="arch-box data">MinIO<br><small>object store</small></div>
      </div>
      <p class="arch-note">TZ-Chat Gateway: auth, conversation management, Dify proxy. Dify: calls RAG as tool. RAG: MinIO docs + Qdrant vector search.</p>
    </div>

    <h2 class="section-title">4. Apply to your project</h2>
    <p class="tagline-sm">Steps to add chat to an existing project (e.g. Vue app)</p>
    <div class="diagram">
      <div class="diagram-title">Integration order</div>
      <div class="flow-row">
        <span class="flow-step">1. Deploy TZ-Chat Gateway</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step">2. Configure env</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step">3. Backend token</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step">4. Frontend widget</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step">5. CORS &amp; CSP</span>
      </div>
      <div class="seq-row">
        <span class="seq-label">1. Deploy</span>
        <span class="seq-box">Run TZ-Chat Gateway on server (Docker/K8s or <code>./gateway.sh</code>). Set JWT secret, Dify API key, <code>CHAT_GATEWAY_API_KEY</code> in <code>.env</code>.</span>
      </div>
      <div class="seq-row">
        <span class="seq-label">2. Env</span>
        <span class="seq-box"><code>CHAT_GATEWAY_JWT_SECRET</code>, <code>CHAT_GATEWAY_API_KEY</code>, <code>DIFY_*_API_KEY</code>. See <code>.env.example</code>, <code>scripts/gen-env-values.sh</code>.</span>
      </div>
      <div class="seq-row">
        <span class="seq-label">3. Backend</span>
        <span class="seq-box">Issue JWT for logged-in users from your backend, or have frontend call <code>GET /v1/chat-token?system_id=...&amp;user_id=...</code> with <code>X-API-Key</code>.</span>
      </div>
      <div class="seq-row">
        <span class="seq-label">4. Frontend</span>
        <span class="seq-box">Copy <code>sample/ChatWidget.vue</code> → wire <code>authService</code> (getUserSync, subscribe) → add <code>&lt;ChatWidget /&gt;</code> in App.vue. Set <code>VUE_APP_CHAT_GATEWAY_URL</code>, <code>VUE_APP_CHAT_GATEWAY_API_KEY</code>.</span>
      </div>
      <div class="seq-row">
        <span class="seq-label">5. CORS·CSP</span>
        <span class="seq-box">Allow your project domain in TZ-Chat Gateway (<code>ALLOWED_CHAT_TOKEN_ORIGINS</code>). If the app has CSP, add TZ-Chat Gateway URL to <code>connect-src</code> and <code>frame-src</code>.</span>
      </div>
      <p class="arch-note">
        Full steps: <a href="https://github.com/doohee323/tz-chatbot/blob/main/chat-gateway/sample/INTEGRATION.md" target="_blank" rel="noopener" class="link">sample/INTEGRATION.md</a>
      </p>
    </div>

    <div class="links">
      <a href="https://github.com/doohee323/tz-chatbot" target="_blank" rel="noopener">GitHub source</a>
      <a href="https://devops.drillquiz.com/" target="_blank" rel="noopener">Sample site (DrillQuiz)</a>
      <a :href="apiBase + '/docs'" target="_blank" rel="noopener">API docs (OpenAPI)</a>
      <router-link to="/chat">Chat page</router-link>
      <a v-if="apiBase" :href="apiBase + '/cache'" target="_blank" rel="noopener">Cache / history (API key required)</a>
    </div>

    <p class="footer">
      Chat page requires a valid JWT (<code>?token=...</code>). Use the chat from DrillQuiz or CoinTutor, or obtain a token via <code>GET /v1/chat-token</code> with <code>X-API-Key</code>.
    </p>
  </div>
</template>

<script>
import { apiBase } from '../config/apiConfig'

export default {
  name: 'About',
  data() {
    return { apiBase }
  }
}
</script>

<style scoped>
.about {
  font-family: "DM Sans", system-ui, -apple-system, sans-serif;
  min-height: 100vh;
  background: var(--bg, #0f172a);
  color: var(--text, #f1f5f9);
}
.wrap { max-width: 900px; margin: 0 auto; padding: 1rem 1.5rem 3rem; }
.tagline { color: var(--muted, #94a3b8); font-size: 1.05rem; margin-bottom: 2rem; }
.tagline-sm { margin-top: 0; margin-bottom: 0.75rem; color: var(--muted, #94a3b8); font-size: 0.95rem; }
.card {
  background: var(--surface, #1e293b);
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.25rem;
  border: 1px solid rgba(255,255,255,0.06);
}
.card h2 { font-size: 1.1rem; font-weight: 600; margin: 0 0 0.75rem; color: var(--accent, #38bdf8); }
.card p { margin: 0; color: var(--muted, #94a3b8); font-size: 0.95rem; }
.link { color: #38bdf8; }
.section-title { font-size: 1.25rem; font-weight: 600; margin: 2.5rem 0 1rem; }
.diagram {
  background: var(--surface, #1e293b);
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.25rem;
  border: 1px solid rgba(255,255,255,0.06);
}
.diagram-title { font-size: 0.8rem; font-weight: 600; color: #38bdf8; margin-bottom: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
.flow-row { display: flex; align-items: center; flex-wrap: wrap; gap: 0.5rem; margin: 0.5rem 0; }
.flow-row.flow-detail { margin-top: 0.75rem; }
.flow-step {
  background: var(--bg, #0f172a);
  border: 1px solid rgba(56, 189, 248, 0.35);
  border-radius: 8px;
  padding: 0.6rem 1rem;
  font-size: 0.9rem;
  color: var(--text, #f1f5f9);
}
.flow-step.user { border-color: rgba(34, 197, 94, 0.5); }
.flow-step.gateway { border-color: rgba(56, 189, 248, 0.5); }
.flow-step.dify { border-color: rgba(168, 85, 247, 0.5); }
.flow-step.rag { border-color: rgba(251, 146, 60, 0.5); }
.flow-arrow { color: var(--muted, #94a3b8); }
.seq-row { display: flex; align-items: center; gap: 0.5rem; margin: 0.35rem 0; font-size: 0.9rem; }
.seq-label { min-width: 6rem; color: var(--muted, #94a3b8); flex-shrink: 0; }
.seq-box {
  flex: 1;
  background: var(--bg, #0f172a);
  border-radius: 6px;
  padding: 0.4rem 0.75rem;
  border: 1px solid rgba(255,255,255,0.08);
  color: var(--muted, #94a3b8);
  font-size: 0.9rem;
}
.arch-arrow-row { text-align: center; margin: 0.25rem 0; color: var(--muted, #94a3b8); font-size: 0.8rem; }
.arch-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.75rem;
  margin: 0.5rem 0;
}
.arch-box {
  background: var(--bg, #0f172a);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  font-size: 0.85rem;
  text-align: center;
  color: var(--text, #f1f5f9);
}
.arch-box.entry { border-color: rgba(34, 197, 94, 0.4); }
.arch-box.gw { border-color: rgba(56, 189, 248, 0.4); }
.arch-box.app { border-color: rgba(168, 85, 247, 0.4); }
.arch-box.data { border-color: rgba(251, 146, 60, 0.4); }
.arch-note { margin: 0.75rem 0 0; font-size: 0.85rem; color: var(--muted, #94a3b8); }
.links { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 2rem; }
.links a {
  display: inline-flex;
  align-items: center;
  padding: 0.6rem 1rem;
  background: var(--surface, #1e293b);
  color: #38bdf8;
  text-decoration: none;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  border: 1px solid rgba(56, 189, 248, 0.25);
}
.links a:hover { background: rgba(56, 189, 248, 0.1); }
.footer { margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid rgba(255,255,255,0.06); font-size: 0.85rem; color: var(--muted, #94a3b8); }
</style>
