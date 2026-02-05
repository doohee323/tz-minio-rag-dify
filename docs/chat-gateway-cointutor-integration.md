# CoinTutor에서 채팅 게이트웨이 사용하기

게이트웨이 채팅 페이지(`/chat?token=<JWT>`)를 CoinTutor에서 여는 방법입니다.  
**전제**: 채팅 게이트웨이와 CoinTutor가 **같은 JWT_SECRET**을 알고 있어야 합니다.

---

## 1. 흐름 요약

1. 사용자가 CoinTutor에 로그인한 상태에서 "채팅 열기" 등을 클릭.
2. CoinTutor **백엔드**가 현재 사용자 ID로 **JWT** 발급 (payload: `system_id`, `user_id`, `exp`).
3. CoinTutor **프론트**가 `https://게이트웨이주소/chat?token=<JWT>` 로 이동(링크/리다이렉트/iframe).
4. 게이트웨이가 JWT를 검증하고 Dify 채팅 페이지를 보여줌.

---

## 2. CoinTutor 백엔드: JWT 발급

게이트웨이 `.env`의 **JWT_SECRET** 값을 CoinTutor 설정(환경변수/설정 파일)에 두고, 아래와 같이 JWT를 만듭니다.

**Payload 예시** (HS256):

- `system_id`: `"cointutor"` (고정)
- `user_id`: CoinTutor 로그인 사용자 ID (문자열)
- `exp`: 만료 시각 (Unix timestamp, 예: 현재 + 1시간)

**예시 (Python)**:

```python
import jwt
import time

JWT_SECRET = "..."  # 게이트웨이 .env와 동일
GATEWAY_CHAT_URL = "https://chat-gateway.example.com"  # 실제 게이트웨이 주소

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

**예시 (Node.js)**:

```javascript
const jwt = require('jsonwebtoken');

const JWT_SECRET = '...';  // 게이트웨이 .env와 동일
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

CoinTutor에서 **API 엔드포인트** 하나 두면 됩니다. 예:

- `GET /api/chat-url` 또는 `GET /api/me/chat-url`  
  - 로그인 세션에서 `user_id` 읽기 → 위 함수로 URL 생성 → `{ "url": "https://.../chat?token=..." }` 반환.

---

## 3. CoinTutor 프론트: 채팅 열기

### 방법 A: 링크(새 탭)

- 버튼/메뉴에 `target="_blank"` 링크로 채팅 URL 넣기.
- URL은 프론트가 백엔드 `GET /api/chat-url` 호출로 받아서 사용.

```html
<a id="open-chat" href="#" target="_blank">채팅 열기</a>
<script>
  fetch('/api/chat-url')
    .then(r => r.json())
    .then(data => { document.getElementById('open-chat').href = data.url; });
</script>
```

### 방법 B: 리다이렉트

- "채팅 열기" 클릭 시 현재 창을 채팅 URL로 이동.

```javascript
fetch('/api/chat-url')
  .then(r => r.json())
  .then(data => { window.location.href = data.url; });
```

### 방법 C: iframe

- CoinTutor 페이지 안에 채팅만 넣고 싶을 때.

```html
<iframe id="chat-frame" style="width:100%; height:600px; border:0;"></iframe>
<script>
  fetch('/api/chat-url')
    .then(r => r.json())
    .then(data => { document.getElementById('chat-frame').src = data.url; });
</script>
```

---

## 4. 설정 체크리스트

| 항목 | 확인 |
|------|------|
| 게이트웨이 `.env`의 `JWT_SECRET` | CoinTutor 백엔드 설정과 **완전히 동일** |
| 게이트웨이 `.env`의 `ALLOWED_SYSTEM_IDS` | `cointutor` 포함 (비어 있으면 모두 허용) |
| 채팅 URL | 실제 게이트웨이 주소 사용 (로컬: `http://localhost:8000`, 운영: `https://...`) |
| JWT 만료 | 너무 길지 않게 (예: 1시간), 필요 시 갱신 |

---

## 5. 정리

- CoinTutor는 **Dify API 키나 embed 토큰을 알 필요 없음**. 게이트웨이만 알면 됨.
- 사용자 식별은 **JWT의 `system_id` + `user_id`** 로만 하면 되고, 게이트웨이가 Dify `user`로 `cointutor_<user_id>` 를 사용함.
- 다른 서비스(예: DrillQuiz)도 같은 방식으로 `system_id`만 바꿔서 쓰면 됨.
