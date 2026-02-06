<template>
  <div class="intro wrap">
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
    <p class="tagline tagline-sm">Check out this repo, use sample apps (DrillQuiz / CoinTutor) as reference to register and apply your app.</p>
    <div class="diagram">
      <div class="diagram-title">Flow: add your app, then use chat</div>
      <div class="flow-row">
        <span class="flow-step">1. Check out this code</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step">2. Register your app (reference: DrillQuiz / CoinTutor)</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step">3. Get token & open chat page</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step">4. Chat</span>
      </div>
    </div>

    <div class="links">
      <router-link to="/about" class="link-btn">About (상세)</router-link>
      <a href="https://github.com/doohee323/tz-chatbot" target="_blank" rel="noopener">GitHub source</a>
      <a :href="apiBase + '/docs'" target="_blank" rel="noopener">API docs (OpenAPI)</a>
      <router-link to="/chat">Chat page</router-link>
    </div>
  </div>
</template>

<script>
import { apiBase } from '../config/apiConfig'

export default {
  name: 'Intro',
  data() {
    return {
      apiBase
    }
  }
}
</script>

<style scoped>
.intro {
  font-family: "DM Sans", system-ui, -apple-system, sans-serif;
  min-height: 100vh;
  background: var(--bg, #0f172a);
  color: var(--text, #f1f5f9);
}
.wrap { max-width: 900px; margin: 0 auto; padding: 1rem 1.5rem 3rem; }
.tagline { color: var(--muted, #94a3b8); font-size: 1.05rem; margin-bottom: 2rem; }
.tagline-sm { margin-top: 0; margin-bottom: 0.75rem; }
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
.diagram-title { font-size: 0.8rem; font-weight: 600; color: #38bdf8; margin-bottom: 0.75rem; }
.flow-row { display: flex; align-items: center; flex-wrap: wrap; gap: 0.5rem; margin: 0.5rem 0; }
.flow-step {
  background: var(--bg, #0f172a);
  border: 1px solid rgba(56, 189, 248, 0.35);
  border-radius: 8px;
  padding: 0.6rem 1rem;
  font-size: 0.9rem;
}
.flow-arrow { color: var(--muted, #94a3b8); }
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
  border: 1px solid rgba(56, 189, 248, 0.25);
}
.links a:hover { background: rgba(56, 189, 248, 0.1); }
.links .link-btn { text-decoration: none; color: inherit; }
</style>
