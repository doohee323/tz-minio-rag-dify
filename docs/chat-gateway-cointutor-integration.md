# Using the chat gateway from CoinTutor

How to open the gateway chat page (`/chat?token=<JWT>`) from CoinTutor.  
**Prerequisite**: The chat gateway and CoinTutor must share the **same JWT_SECRET**.

---

## 1. Flow summary

1. User is logged into CoinTutor and clicks "Open chat" (or similar).
2. CoinTutor **backend** issues a **JWT** for the current user (payload: `system_id`, `user_id`, `exp`).
3. CoinTutor **frontend** navigates to `https://<gateway-host>/chat?token=<JWT>` (link, redirect, or iframe).
4. Gateway validates the JWT and shows the Dify chat page.

---

## 2. CoinTutor backend: issuing JWT

Store the gateway `.env` **JWT_SECRET** in CoinTutor config (env or config file) and create the JWT as below.

**Payload example** (HS256):

- `system_id`: `"cointutor"` (fixed)
- `user_id`: CoinTutor logged-in user ID (string)
- `exp`: Expiry time (Unix timestamp, e.g. now + 1 hour)

**Example (Python)**:

```python
import jwt
import time

JWT_SECRET = "..."  # Same as gateway .env
GATEWAY_CHAT_URL = "https://chat-gateway.example.com"  # Actual gateway URL

def get_chat_url(user_id: str, expires_in_seconds: int = 3600) -> str:
    payload = {
        "system_id": "cointutor",
        "user_id": str(user_id),
        "exp": int(time.time()) + expires_in_seconds,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    if hasattr(token, "decode"):
        token = token.decode("utf-8")
    return f"{GATEWAY_CHAT_URL}/chat?token={token}"
```

**Example (Node.js)**:

```javascript
const jwt = require('jsonwebtoken');

const JWT_SECRET = '...';  // Same as gateway .env
const GATEWAY_CHAT_URL = 'https://chat-gateway.example.com';

function getChatUrl(userId, expiresInSeconds = 3600) {
  const token = jwt.sign(
    {
      system_id: 'cointutor',
      user_id: String(userId),
      exp: Math.floor(Date.now() / 1000) + expiresInSeconds,
    },
    JWT_SECRET,
    { algorithm: 'HS256' }
  );
  return `${GATEWAY_CHAT_URL}/chat?token=${token}`;
}
```

Expose one **API endpoint** in CoinTutor, e.g.:

- `GET /api/chat-url` or `GET /api/me/chat-url`  
  - Read `user_id` from the login session → build URL with the function above → return `{ "url": "https://.../chat?token=..." }`.

---

## 3. CoinTutor frontend: opening chat

### Option A: Link (new tab)

- Set the chat URL on a button/menu link with `target="_blank"`.
- Frontend gets the URL by calling backend `GET /api/chat-url`.

```html
<a id="open-chat" href="#" target="_blank">Open chat</a>
<script>
  fetch('/api/chat-url')
    .then(r => r.json())
    .then(data => { document.getElementById('open-chat').href = data.url; });
</script>
```

### Option B: Redirect

- On "Open chat" click, navigate the current window to the chat URL.

```javascript
fetch('/api/chat-url')
  .then(r => r.json())
  .then(data => { window.location.href = data.url; });
```

### Option C: iframe

- When you want chat embedded inside a CoinTutor page.

```html
<iframe id="chat-frame" style="width:100%; height:600px; border:0;"></iframe>
<script>
  fetch('/api/chat-url')
    .then(r => r.json())
    .then(data => { document.getElementById('chat-frame').src = data.url; });
</script>
```

---

## 4. Setup checklist

| Item | Check |
|------|-------|
| Gateway `.env` `JWT_SECRET` | **Exactly the same** as CoinTutor backend config |
| Gateway `.env` `ALLOWED_SYSTEM_IDS` | Includes `cointutor` (empty = allow all) |
| Chat URL | Use real gateway URL (local: `http://localhost:8000`, prod: `https://...`) |
| JWT expiry | Keep short (e.g. 1 hour); refresh when needed |

---

## 5. Summary

- CoinTutor does **not** need to know Dify API keys or embed tokens; only the gateway.
- User identity is **JWT `system_id` + `user_id`**; the gateway uses Dify `user` as `cointutor_<user_id>`.
- Other services (e.g. DrillQuiz) can use the same pattern with a different `system_id`.
