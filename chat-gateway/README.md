# TZ-Chat Gateway

**Chat gateway** in front of Dify: client systems (DrillQuiz, CoinTutor, etc.) call this API only; users and conversations are managed centrally by the gateway.

---

## Intro page (root URL)

When the server is running, the **root URL** (`http://localhost:8088/` or `https://<gateway-host>/`) serves an intro page that describes:

- **What TZ-Chat Gateway is** and how it fits in the tz-minio-rag-dify stack
- **Workflow**: check out this repo → register your app (using sample apps DrillQuiz / CoinTutor as reference) → get token & open chat → chat
- **How the app operates**: request flow from client through the gateway and Dify to RAG, then back
- **Architecture**: components (Ingress, TZ-Chat Gateway, Dify, RAG Backend, Qdrant, MinIO) and their roles
- **Apply to your project**: steps to add chat to an existing app (deploy gateway, env, backend token, frontend widget, CORS & CSP)

The page also links to the **sample integration site** ([devops.drillquiz.com](https://devops.drillquiz.com/)), GitHub source, API docs (`/docs`), chat page (`/chat`), and cache/history UI (`/cache`).

---

## Usage

### 1) Chat page (use in browser)

After starting the gateway server, open a **URL that includes a JWT** to see the chat UI; **all sent messages are stored in the DB**.

1. Start server: `./local.sh`
2. Generate a test JWT (**from the chat-gateway directory**):
   ```bash
   cd chat-gateway
   ./scripts/gen-jwt.sh
   ./scripts/gen-jwt.sh cointutor 999
   ```
3. Open the printed URL (`http://localhost:8088/chat?token=<JWT>`) in a browser. `/chat-api?token=<JWT>` shows the same page.

### 2) Use via API (from other services)

Call the gateway API from another backend (DrillQuiz, CoinTutor, etc.).

- **Auth**: Add header `X-API-Key: <CHAT_GATEWAY_API_KEY value>`
- **Send message**: `POST http://localhost:8088/v1/chat`  
  Body (JSON): `{"system_id": "drillquiz", "user_id": "12345", "message": "Hello"}`
- **List conversations**: `GET http://localhost:8088/v1/conversations?system_id=drillquiz&user_id=12345`  
  (same header with `X-API-Key` required)

See **http://localhost:8088/docs** for full request/response details.

### 3) Sending users to the chat page from your system

When users click "Open chat" in DrillQuiz, **CoinTutor**, etc., send them to the gateway chat page.

- **Issue JWT** from your backend (payload: `system_id`, `user_id`, `exp`; sign with the **same CHAT_GATEWAY_JWT_SECRET** as the gateway)
- **Redirect** or link/iframe: `https://<gateway-host>/chat?token=<issued_JWT>`

**CoinTutor integration details**: [../docs/chat-gateway-cointutor-integration.md](../docs/chat-gateway-cointutor-integration.md) (backend JWT example, frontend link/iframe example)

---

## Spec

| Item | Description |
|------|-------------|
| **Language** | Python 3.11+ |
| **Framework** | FastAPI |
| **DB** | SQLite (default); switchable via env to PostgreSQL etc. |
| **Auth** | API Key (header `X-API-Key`) or JWT (query `token` or header `Authorization: Bearer <jwt>`) |
| **Dify** | httpx async calls, `user` = `{system_id}_{user_id}` |

### Main environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DIFY_BASE_URL` | ✅ | Dify API base URL (shared). Used when per-system value is not set |
| `DIFY_API_KEY` | ✅ | Dify API key (shared). Used when per-system value is not set |
| `DIFY_DRILLQUIZ_BASE_URL` / `DIFY_DRILLQUIZ_API_KEY` | Optional | DrillQuiz-specific Dify (empty = use shared) |
| `DIFY_COINTUTOR_BASE_URL` / `DIFY_COINTUTOR_API_KEY` | Optional | CoinTutor-specific Dify (empty = use shared) |
| `CHAT_GATEWAY_JWT_SECRET` | ✅ (for chat page) | Secret for JWT sign/verify |
| `CHAT_GATEWAY_API_KEY` | Optional | API key auth. Comma-separated list (e.g. `key_drillquiz_xxx,key_cointutor_yyy`). Empty = API key disabled |
| `DATABASE_URL` | Optional | Default `sqlite:///./chat_gateway.db` |
| `ALLOWED_SYSTEM_IDS` | Optional | Allowed `system_id` list, comma-separated. Empty = allow all |
| `ALLOWED_CHAT_TOKEN_ORIGINS` | Optional | CORS allowed origins (comma-separated). Empty = us-dev/us/us-qa.drillquiz.com + localhost etc. Required for `/v1/chat-token` calls |

### API summary

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/chat` | Send message. Body: `system_id`, `user_id`, `message`, (optional) `conversation_id`. API Key or JWT |
| GET | `/v1/conversations` | Query: `system_id`, `user_id`. List conversations for that user |
| GET | `/v1/conversations/{id}/messages` | List messages for a conversation (via Dify API) |
| POST | `/v1/sync` | Fetch conversation list and messages from Dify into SQLite. API Key required. Run periodically (e.g. cron) |
| GET | `/v1/cache/conversations` | List cached conversations. Query: `system_id`, `user_id`, `from_date`, `to_date`. **X-API-Key** required |
| GET | `/v1/cache/conversations/{id}/messages` | List cached messages. **X-API-Key** required |
| GET | `/cache` | **Conversation history web UI**. Query: `api_key=xxx` (required). Filter by system, user, date range |
| GET | `/chat` | Query: `token=<JWT>`. Chat page. All sent messages are stored in DB |
| GET | `/chat-api` | Same as above (alias) |
| GET | `/v1/chat-token` | Query: `system_id`, `user_id`. Header `X-API-Key` required. Issue JWT for chat (DrillQuiz: logged in = username, not logged in = anonymous) |

### Run

```bash
cd chat-gateway
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # edit and save
uvicorn app.main:app --reload --host 0.0.0.0 --port 8088
```

- API docs: http://localhost:8088/docs  
- Chat page example: `http://localhost:8088/chat?token=<JWT>&embed=1` (embed=1 for widget)
- **Conversation history UI**: `https://<gateway-domain>/cache?api_key=<key registered in CHAT_GATEWAY_API_KEY>`  
  - Example: `https://chat.drillquiz.com/cache?api_key=YOUR_KEY`  
  - Filter cached conversations and messages by system, user, and date range. API Key required.

### How to set environment variable values

| Variable | How to set |
|----------|------------|
| **DIFY_BASE_URL** | Dify base URL as you use it. e.g. `https://dify.drillquiz.com` |
| **DIFY_API_KEY** | Dify Studio → select **chat app** → **API Access** → copy **API Key** (format: `app-xxxx...`) |
| **DIFY_DRILLQUIZ_*** / **DIFY_COINTUTOR_*** | Only when DrillQuiz and CoinTutor use different Dify apps/domains. Set `_BASE_URL` and `_API_KEY` for each. |
| **CHAT_GATEWAY_JWT_SECRET** | Any random string. Generate: `openssl rand -hex 32` |
| **CHAT_GATEWAY_API_KEY** | Choose one per service, comma-separated. e.g. `key_drillquiz_abc123`, `key_cointutor_def456`. Generate: `openssl rand -hex 16` |

- Empty `CHAT_GATEWAY_API_KEY` disables API key auth (JWT only).
- Empty `ALLOWED_SYSTEM_IDS` allows any `system_id`.
- **`ALLOWED_CHAT_TOKEN_ORIGINS`**: Origins allowed to call `/v1/chat-token` (comma-separated). e.g. `http://localhost:8080` for DrillQuiz frontend. Empty = allow all origins.

**Generate in one go** (only CHAT_GATEWAY_JWT_SECRET and CHAT_GATEWAY_API_KEY):

```bash
./scripts/gen-env-values.sh
```

Copy the output into `.env`, then paste `DIFY_API_KEY` from Dify **API Access**.

### Frontend chat token API (DrillQuiz etc.)

Instead of issuing JWT manually, the frontend can **get a token via API**.

- **GET /v1/chat-token**: Query `system_id`, `user_id` (required). Header **X-API-Key**. Response `{ "token": "<JWT>" }` (24h validity).
- DrillQuiz .env: `VUE_APP_CHAT_GATEWAY_URL`, **VUE_APP_CHAT_GATEWAY_API_KEY** (same as chat-gateway `CHAT_GATEWAY_API_KEY`). Optional: `VUE_APP_CHAT_GATEWAY_SYSTEM_ID=drillquiz`. **user_id**: when logged in use **username**, when not **anonymous**.
- Set **ALLOWED_CHAT_TOKEN_ORIGINS=http://localhost:8080** etc. in chat-gateway .env so only those origins can call `/v1/chat-token`.

**Add chat widget to Vue app**: See [sample/INTEGRATION.md](sample/INTEGRATION.md) for step-by-step instructions and the **sample/** folder (ChatWidget.vue, env example, authService adapter).

### JWT issuance (from your system, manual)

Example JWT (HS256) when your system sends users to the chat page:

- Payload: `{"system_id": "drillquiz", "user_id": "12345", "exp": <expiry_timestamp>}`  
- Sign with `CHAT_GATEWAY_JWT_SECRET`.  
- Redirect to gateway `/chat?token=<jwt>`; gateway verifies and shows the chat page.

---

## Storing conversations in SQLite

- **On each message**: When you send a message via **POST /v1/chat**, right after the Dify response it is written to **conversation_cache** and **message_cache**. No separate sync step.
- **POST /v1/sync** (header `X-API-Key` required): For each registered (system_id, user_id), fetches conversation list and messages from Dify **Service API** and upserts into the cache. Use to backfill or fix data from other flows.
- **Sync scope**: `ConversationMapping` (from POST /v1/chat usage) + **SyncUser** (auto-registered on /chat and /chat-api access).

- **Periodic run**: e.g. cron: `curl -X POST http://localhost:8088/v1/sync -H "X-API-Key: YOUR_KEY"` every 5 minutes.

---

## Architecture

```
[DrillQuiz / CoinTutor / ...] → [TZ-Chat Gateway] → Dify API
                                      ↓
                               SQLite (conversation mapping + conversation_cache, message_cache)
```

- To add a new client: issue an API key (or use same CHAT_GATEWAY_JWT_SECRET + system_id rules) at the gateway; no Dify call logic needed in the client.

---

## Project structure

```
chat-gateway/
├── README.md
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py          # FastAPI app, router registration
│   ├── config.py        # Env config
│   ├── auth.py          # API Key / JWT validation
│   ├── database.py      # SQLAlchemy async engine, session
│   ├── models.py        # ConversationMapping, ConversationCache, MessageCache
│   ├── sync_service.py  # Dify → SQLite sync
│   ├── schemas.py       # Request/response Pydantic models
│   ├── dify_client.py   # Dify API client
│   ├── templates.py     # Jinja2 templates
│   └── routers/
│       ├── index.py     # GET / (intro page)
│       ├── chat.py      # POST/GET /v1/chat, /v1/conversations, ...
│       └── chat_page.py # GET /chat?token=<JWT>
├── templates/
│   ├── index.html       # Intro page (root /): workflow, architecture, apply-to-project, sample site link
│   └── chat_api.html    # Chat page (conversation list, messages, send, DB recording)
└── sample/              # Vue integration: widget component, env example, integration guide
    ├── INTEGRATION.md   # Integration steps (copy files, authService, env, CI)
    ├── ChatWidget.vue
    ├── App.vue.snippet
    ├── env-frontend.example
    └── authService.adapter.example.js
```
