# DrillQuiz + Dify chat integration: user identity, tracking, and F/U

Example chatbot URL: `https://dify.drillquiz.com/chatbot/5J5xj0G2GHxEglrL`  
When providing chat via **iframe/embed** or **API proxy** from the DrillQuiz site, this doc summarizes **how to pass DrillQuiz user identity and how to track and follow up (F/U)**.

---

## 1. How Dify identifies users

- In the **Service API (chat API)**, the **`user` query parameter** is the **user identifier**.
- Only conversations created with the same `user` value can be grouped and managed together.
- Reference: [Dify API - Get Conversations](https://docs.dify.ai/api-reference/conversations/get-conversations) — `user` (required), `Authorization: Bearer app-xxx`

**Summary**: Pass the DrillQuiz user ID (e.g. `drillquiz_user_12345`) as the `user` parameter when calling the Dify API; then you can track and query “who had which conversation”.

---

## 2. How to pass user identity by chat delivery method

### A. Dify Chatbot **embed** on the DrillQuiz site

- Add the **chat widget (embed)** to the DrillQuiz web app and set **logged-in user info** before loading the script.

```html
<script>
  window.difyChatbotConfig = {
    token: 'app-5J5xj0G2GHxEglrL',  // use actual token from the app
    baseUrl: 'https://dify.drillquiz.com',
    // DrillQuiz logged-in user ID → pass as Dify user identifier
    inputs: {
      user_id: 'drillquiz_12345',   // inject at server render time
      email: 'user@example.com'    // optional
    }
  };
</script>
<script src="https://dify.drillquiz.com/embed.min.js" defer></script>
```

- Values in `inputs` can be used as **workflow variables**.  
- Check the embed script/docs for **where Dify Chat/API gets `user`**.  
  - If the embed does **not** send `inputs.user_id` as the API `user`, use approach B below and have the **DrillQuiz backend proxy** calls and set `user` explicitly.

### B. DrillQuiz backend **proxies** Dify API (most reliable)

- Users log in only on the **DrillQuiz web/app**. Chat requests go to the **DrillQuiz backend**.
- The DrillQuiz backend calls the **Dify Service API** to send messages and **includes `user` = DrillQuiz user ID on every request**.

```
[User] → DrillQuiz frontend → DrillQuiz backend → Dify API (user=drillquiz_user_12345)
```

- Then §4 (auth), §5 (tracking), §6 (F/U) can all be **driven by DrillQuiz**.
- Dify API example (send chat message):
  - `POST /v1/chat-messages`  
  - Query: `user=drillquiz_user_12345`  
  - Body: `inputs`, `query`, `conversation_id` etc. (see Dify API docs)

- **Downside**: Each system (DrillQuiz, CoinTutor, etc.) that adds chat must implement Dify API calls and user mapping.

---

## 3. Managing users and conversations on the chat side (minimal changes to client systems)

**Goal**: When adding chat to a new service, **change the client system as little as possible** and **manage user identity, conversation content, and F/U in one place** (the chat app or a dedicated API).

**Relation to embed/iframe**  
- You **can** use Dify’s iframe/embed.  
- But if you want “**central management** of users and conversations”, embed alone is **not enough**:  
  - Putting embed **directly on each system’s page** keeps identity, conversation list, and F/U scattered across those systems or Dify, and each new service needs its own setup/code.  
- A **gateway** allows **reusing embed**.  
  - The gateway provides a “chat page that loads the embed”; client systems only send users to that page (§3.1 options 1–2).  
- **Summary**: To meet the “central management” requirement you need a **gateway (or separate web app)**; whether you use embed on top is optional.

### 3.1 Shared chat gateway API + web app (recommended)

**Setup**: Put a **chat API server (and optionally a chat web app)** in front of Dify.

```
[Client systems A/B/C] → [Chat gateway API] → Dify API
                              ↓
                       (Own DB: user–conversation mapping, logs)
```

- **Gateway API** responsibilities:
  1. **Unified chat API**  
     - e.g. `POST /v1/chat` — Body or Header: `system_id` (e.g. drillquiz, cointutor), `user_id` (client system user ID), `message`, (optional) `conversation_id`.  
     - Gateway builds Dify `user` as `{system_id}_{user_id}` and calls Dify. Only the gateway holds the Dify API key.
  2. **User and conversation management**  
     - Store `(system_id, user_id)` ↔ `conversation_id`, timestamps, (optional) message summary in its own DB.  
     - Read API: `GET /v1/conversations?system_id=drillquiz&user_id=12345` → that user’s conversations. `GET /v1/conversations/:id/messages` → messages (from Dify API or gateway cache/sync).
  3. **Auth**  
     - Client systems call the gateway with **API key** or **signed token (JWT)**. Gateway derives `system_id`, `user_id` from the token.  
     - Adding a new service = register `system_id` at the gateway and issue an API key (or signing key). **No Dify call logic in client code.**

- **Chat UI** (optional):
  - **Option 1**: Gateway serves a **chat window page**. On “Open chat”, the client redirects to `https://chat-admin.example.com/chat?token=<JWT>`. JWT contains `system_id`, `user_id`, expiry. Gateway validates the token and shows Dify embed or its own UI (calling the above API to Dify internally).
  - **Option 2**: Client keeps using embed, but the **page that loads the embed** is served by the gateway. On entry, gateway validates the token and injects `difyChatbotConfig.inputs` or sets `user` on API calls.

- **Result**  
  - User identity, conversation history, stats, and F/U are managed in **one place (gateway + its DB)**.  
  - DrillQuiz, CoinTutor, etc. only “call the gateway API” or “send users to the gateway chat URL”, so **each system needs minimal changes when adding chat.**

### 3.2 Required APIs (gateway design example)

| API | Purpose |
|-----|---------|
| `POST /v1/chat` | Send message. Body/Header: `system_id`, `user_id`, `message`, (optional) `conversation_id`. Gateway calls Dify and stores conversation mapping in its DB. |
| `GET /v1/conversations` | List conversations for a user by `system_id`, `user_id` (gateway DB or Dify `GET /conversations?user=xxx`). |
| `GET /v1/conversations/:id/messages` | List messages for a conversation (Dify API or gateway cache). |
| `GET /v1/chat` (or chat page) | After validating JWT, serve chat UI. Token includes `system_id`, `user_id`. |

- If you run a **separate web app**: deploy backend that exposes these APIs + a “chat window” frontend (for redirect or embed hosting) as one service.

---

## 4. What to do for §4, §5, §6

| Goal | How |
|------|-----|
| **§4 iframe/embed auth** | (A) embed: Expose DrillQuiz page only to logged-in users. (B) API proxy: Backend validates session then calls Dify. **(3.1 Gateway)** Gateway validates token and then serves chat/API. |
| **§5 User and request tracking** | Use **`user` = (system_id + user_id)** consistently. With the gateway, use gateway DB + Dify API to query conversation list and stats in one place. |
| **§6 Chat F/U** | Store (system_id, user_id) ↔ conversation_id in the gateway DB. Support/ops UI calls gateway API for “conversations and messages per user” and links to tickets/issues. |

---

## 5. User identity: extract and manage

- **Extract**: Pass **client system + user identifier** (e.g. `drillquiz_12345`) to Dify (or the gateway).  
  - (A) embed: Inject at server render via `inputs.user_id` etc.  
  - (B) API proxy: Backend reads user ID from session and passes as `user`.  
  - **(3.1 Gateway)**: Client sends only `system_id` + `user_id` (or JWT); gateway builds `user`, calls Dify, and stores in DB.
- **Manage**:
  - **With gateway**: Users, conversations, and stats live in the **gateway DB + API**. Client systems only call the gateway API.
  - **Without gateway (only A or B)**: Store `user_id` ↔ `conversation_id` in that system’s DB and use Dify API `GET /conversations?user=xxx` to query/sync.

**Summary**: To avoid changing each client system whenever you add chat, use a **shared chat gateway API (and optional chat web app)** and manage user identity, conversation content, and F/U on the chat side (gateway) as in §3.1.
