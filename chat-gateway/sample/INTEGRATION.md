# How to Add the Chat Module (Vue app)

This document describes how to add the chat widget (as used in tz-drillquiz) to another Vue project.

## Prerequisites

- **Chat Gateway** server must be deployed, and you must have one of the `CHAT_GATEWAY_API_KEY` API keys.
- The Vue 2/3 project must have an **auth service** or be able to implement a minimal interface (authService adapter).

---

## 1. Copy files

| Source (sample) | Target (project) |
|-----------------|------------------|
| `sample/ChatWidget.vue` | `src/components/ChatWidget.vue` |

```bash
cp chat-gateway/sample/ChatWidget.vue your-vue-app/src/components/ChatWidget.vue
```

---

## 2. Auth service (authService) integration

ChatWidget expects the following interface:

- **`authService.getUserSync()`**  
  - Returns: `{ username: string }` or `null`  
  - Logged-in user: return `username` (or user identifier)  
  - Not logged in: `null` → widget sends `user_id` as `anonymous`

- **`authService.subscribe(handler)`**  
  - Register a callback to be invoked when auth state changes  
  - Returns: unsubscribe function (call when component is destroyed)

### 2-1. When you already have authService

- Either make `getUserSync()` return `{ username }`, or
- Adjust the field used in ChatWidget’s `getChatUserId()` (id, email, etc.) to match your project in one place.

### 2-2. When you don’t have authService

- Copy `sample/authService.adapter.example.js` to `src/services/authService.js`, then
- Wire your login/logout to call `setAuthUser(user)` or `setAuthUser(null)`.

---

## 3. Update App.vue

- **import**: Add the `ChatWidget` component
- **components**: Register `ChatWidget`
- **template**: Add a single line `<ChatWidget />` at the bottom of the layout (e.g. after Footer)

See `App.vue.snippet` for exact code snippets.

```vue
<template>
  <div id="app">
    <!-- ... existing layout ... -->
    <AppFooter />
    <ChatWidget />
  </div>
</template>

<script>
import ChatWidget from '@/components/ChatWidget.vue'
// ...
export default {
  components: {
    AppFooter,
    ChatWidget
  },
  // ...
}
</script>
```

---

## 4. Environment variables

The following env vars are required at build time. Use `.env` locally and replace placeholders in `env-frontend` etc. for CI.

| Variable | Description | Example |
|----------|-------------|---------|
| `VUE_APP_CHAT_GATEWAY_URL` | Chat Gateway base URL (no trailing `/`) | `https://chat.drillquiz.com` |
| `VUE_APP_CHAT_GATEWAY_API_KEY` | Gateway API key (one of CHAT_GATEWAY_API_KEY) | (injected by Jenkins/CI) |
| `VUE_APP_CHAT_GATEWAY_SYSTEM_ID` | System identifier (must match gateway ALLOWED_SYSTEM_IDS) | `drillquiz` |

Example file: `env-frontend.example`

### 4-1. Local development (DrillQuiz)

- Vue CLI only auto-loads `.env` / `.env.local`. To use `env-frontend`, have **vue.config.js** read `env-frontend` at build time and attach it to `process.env`.
- Then set URL/API key in `env-frontend` and restart `npm run serve` for the widget to work.

---

## 5. i18n (optional)

- If the app uses `vue-i18n`, the widget can pass `this.$i18n.locale` as the `lang` parameter when the gateway supports it.
- Supported locales: `en`, `es`, `ko`, `zh`, `ja` (for gateway chat UI/response language when applicable).

---

## 6. CI build (e.g. Jenkins)

- When Chat Gateway domain/API key differ per branch:
  - In `env-frontend` set `VUE_APP_CHAT_GATEWAY_URL=https://chat.drillquiz.com` (fixed),  
    `VUE_APP_CHAT_GATEWAY_API_KEY=CHAT_GATEWAY_API_KEY_PLACEHOLDER`,
  - In the build script replace `CHAT_GATEWAY_API_KEY_PLACEHOLDER` with the API key from Jenkins credentials etc.

### 6-1. This project (DrillQuiz) summary

- **Jenkins**
  - Credential ID: `CHAT_GATEWAY_API_KEY` (Secret text). If missing, only the chat widget is disabled; build continues.
  - `ci/Jenkinsfile`: In Load Credentials stage load that credential; in Build Frontend stage run `export CHAT_GATEWAY_API_KEY` then `ci/k8s.sh build-frontend`.
- **ci/k8s.sh**
  - `build_frontend`: sed-replace only `CHAT_GATEWAY_API_KEY_PLACEHOLDER` in `env-frontend`. `VUE_APP_CHAT_GATEWAY_URL` is fixed to https://chat.drillquiz.com.
- **Local development**
  - `vue.config.js` loads `env-frontend` into `process.env`, so set URL/key in `env-frontend` and restart `npm run serve` for the widget.

---

## 7. Flow summary

1. User clicks the chat button (bottom right).
2. Call `GET /v1/chat-token?system_id=...&user_id=...` with `X-API-Key` to get a JWT.
3. Open iframe with `chat URL?token=...&embed=1`.
4. Logged-in users use `user_id` = username; otherwise `anonymous`.

---

## 8. CSP (Content-Security-Policy)

When the app sets a **Content-Security-Policy** header, the chat widget needs:

- **connect-src**  
  Include `https://chat.drillquiz.com` so `fetch('https://chat.drillquiz.com/v1/chat-token?...')` is allowed.
- **frame-src**  
  Include `https://chat.drillquiz.com` so the chat UI iframe `https://chat.drillquiz.com/chat?token=...` can load.

Example (e.g. Ingress nginx `configuration-snippet`):

```text
connect-src 'self' ... https://chat.drillquiz.com;
frame-src 'self' https://chat.drillquiz.com;
```

If not set, the browser console will show  
"Refused to connect ... violates the document's Content Security Policy" and the token request or iframe will be blocked.

---

## sample folder contents

| File | Purpose |
|------|---------|
| `ChatWidget.vue` | Widget component (Vue 2 compatible: beforeDestroy, transition enter/leave). Copy and use |
| `App.vue.snippet` | Snippets for import/registration/template in App.vue |
| `env-frontend.example` | Frontend build env example (fixed URL, CI placeholder: CHAT_GATEWAY_API_KEY_PLACEHOLDER) |
| `authService.adapter.example.js` | Minimal authService implementation when you don’t have one |
| `INTEGRATION.md` | This integration guide |

### Jenkins credentials

- To enable the chat widget in CI, add a **Secret text** credential in Jenkins.
- **ID:** `CHAT_GATEWAY_API_KEY` (Jenkinsfile looks up by this ID)
- **Value:** An API key issued by the Chat Gateway (one of CHAT_GATEWAY_API_KEY)
