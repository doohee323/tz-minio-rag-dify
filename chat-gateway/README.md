# Chat Gateway

Dify 앞단의 **채팅 게이트웨이**: 대상 시스템(DrillQuiz, CoinTutor 등)은 이 API만 호출하고, 사용자·대화는 게이트웨이에서 일괄 관리합니다.

---

## 사용 방법

### 1) 채팅 페이지 (브라우저에서 바로 사용)

게이트웨이 서버를 띄운 뒤, **JWT가 붙은 URL**로 접속하면 채팅 화면이 열리고, **보낸 대화는 모두 DB에 기록**됩니다.

1. 서버 실행: `./local.sh`
2. 테스트용 JWT 발급 (**chat-gateway 디렉터리에서** 실행):
   ```bash
   cd chat-gateway
   ./scripts/gen-jwt.sh
   ./scripts/gen-jwt.sh cointutor 999
   ```
3. 출력된 URL(`http://localhost:8088/chat?token=<JWT>`)을 브라우저에서 열기. `/chat-api?token=<JWT>` 도 동일한 화면.

### 2) API로 사용 (다른 서비스에서 호출)

다른 백엔드(DrillQuiz, CoinTutor 등)에서 게이트웨이 API를 호출하는 방식입니다.

- **인증**: 요청 헤더에 `X-API-Key: <CHAT_GATEWAY_API_KEY 값>` 추가
- **메시지 전송**: `POST http://localhost:8088/v1/chat`  
  Body (JSON): `{"system_id": "drillquiz", "user_id": "12345", "message": "안녕하세요"}`
- **대화 목록**: `GET http://localhost:8088/v1/conversations?system_id=drillquiz&user_id=12345`  
  (같은 헤더에 `X-API-Key` 필요)

자세한 요청/응답은 **http://localhost:8088/docs** 에서 확인할 수 있습니다.

### 3) 대상 시스템에서 채팅 페이지로 보내기

DrillQuiz, **CoinTutor** 등에서 "채팅 열기" 버튼을 누르면 게이트웨이 채팅 페이지로 이동시키는 방법입니다.

- 해당 시스템 백엔드에서 **JWT 발급** (payload: `system_id`, `user_id`, `exp`, 서명: 게이트웨이와 **동일한 CHAT_GATEWAY_JWT_SECRET**)
- 사용자를 **리다이렉트** 또는 **링크/iframe**: `https://게이트웨이주소/chat?token=<발급한_JWT>`

**CoinTutor 연동 상세**: [../docs/chat-gateway-cointutor-integration.md](../docs/chat-gateway-cointutor-integration.md) (백엔드 JWT 발급 예시, 프론트 링크/iframe 예시)

---

## 스펙

| 항목 | 내용 |
|------|------|
| **언어** | Python 3.11+ |
| **프레임워크** | FastAPI |
| **DB** | SQLite (기본), 환경변수로 PostgreSQL 등으로 전환 가능 |
| **인증** | API Key (Header `X-API-Key`) 또는 JWT (Query `token` 또는 Header `Authorization: Bearer <jwt>`) |
| **Dify 연동** | httpx 비동기 호출, `user` = `{system_id}_{user_id}` |

### 주요 환경변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `DIFY_BASE_URL` | ✅ | Dify API 베이스 URL (공통). 시스템별 미설정 시 사용 |
| `DIFY_API_KEY` | ✅ | Dify API 키 (공통). 시스템별 미설정 시 사용 |
| `DIFY_DRILLQUIZ_BASE_URL` / `DIFY_DRILLQUIZ_API_KEY` | 선택 | DrillQuiz 전용 Dify (비우면 공통 값 사용) |
| `DIFY_COINTUTOR_BASE_URL` / `DIFY_COINTUTOR_API_KEY` | 선택 | CoinTutor 전용 Dify (비우면 공통 값 사용) |
| `CHAT_GATEWAY_JWT_SECRET` | ✅ (채팅 페이지 사용 시) | JWT 서명/검증용 시크릿 |
| `CHAT_GATEWAY_API_KEY` | 선택 | API Key 인증용. 쉼표 구분 가능 (예: `key_drillquiz_xxx,key_cointutor_yyy`). 비우면 API Key 비활성화 |
| `DATABASE_URL` | 선택 | 기본 `sqlite:///./chat_gateway.db` |
| `ALLOWED_SYSTEM_IDS` | 선택 | 허용 `system_id` 목록, 쉼표 구분. 비우면 모두 허용 |

### API 요약

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/v1/chat` | 메시지 전송. Body: `system_id`, `user_id`, `message`, (선택) `conversation_id`. API Key 또는 JWT |
| GET | `/v1/conversations` | 쿼리: `system_id`, `user_id`. 해당 사용자 대화 목록 |
| GET | `/v1/conversations/{id}/messages` | 특정 대화 메시지 목록 (Dify API 조회) |
| POST | `/v1/sync` | Dify에서 대화 목록·메시지를 가져와 SQLite에 저장. API Key 필요. cron으로 주기 호출 권장 |
| GET | `/v1/cache/conversations` | 캐시된 대화 목록 조회. 쿼리: `system_id`, `user_id`, `from_date`, `to_date`. **X-API-Key** 필요 |
| GET | `/v1/cache/conversations/{id}/messages` | 캐시된 메시지 목록. **X-API-Key** 필요 |
| GET | `/cache` | **대화 이력 조회 웹 페이지**. 쿼리: `api_key=xxx` (필수). 시스템·사용자·기간으로 조회 |
| GET | `/chat` | 쿼리: `token=<JWT>`. 채팅 페이지. 보낸 대화는 모두 DB 기록 |
| GET | `/chat-api` | 위와 동일 (별칭) |
| GET | `/v1/chat-token` | 쿼리: `system_id`, `user_id`. 헤더 `X-API-Key` 필요. 채팅용 JWT 발급 (DrillQuiz: 로그인=username, 비로그인=anonymous) |

### 실행

```bash
cd chat-gateway
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # 편집 후 저장
uvicorn app.main:app --reload --host 0.0.0.0 --port 8088
```

- API 문서: http://localhost:8088/docs  
- 채팅 페이지 예: `http://localhost:8088/chat?token=<JWT>&embed=1&lang=en` (embed=1 위젯용, lang= en|es|ko|zh|ja, 없으면 브라우저 언어)
- **대화 이력 조회 화면**: `https://<게이트웨이 도메인>/cache?api_key=<CHAT_GATEWAY_API_KEY에 등록된 키>`  
  - 운영 예: `https://chat.drillquiz.com/cache?api_key=YOUR_KEY`  
  - 시스템·사용자·기간 필터로 캐시된 대화 목록과 메시지를 조회. API Key 필수.

### 환경변수 값 만드는 방법

| 변수 | 만드는 방법 |
|------|-------------|
| **DIFY_BASE_URL** | Dify 접속 주소 그대로. 예: `https://dify.drillquiz.com` |
| **DIFY_API_KEY** | Dify 스튜디오 → 사용할 **채팅 앱** 선택 → **API Access** 메뉴 → **API Key** 복사 (형식: `app-xxxx...`) |
| **DIFY_DRILLQUIZ_*** / **DIFY_COINTUTOR_*** | DrillQuiz·CoinTutor가 **서로 다른 Dify 앱/도메인**일 때만 설정. 각각 `_BASE_URL`, `_API_KEY` |
| **CHAT_GATEWAY_JWT_SECRET** | 아무 랜덤 문자열. 터미널에서 생성: `openssl rand -hex 32` |
| **CHAT_GATEWAY_API_KEY** | 서비스별로 하나씩 정해서 쉼표로 나열 가능. 예: DrillQuiz용 `key_drillquiz_abc123`, CoinTutor용 `key_cointutor_def456`. 랜덤 생성: `openssl rand -hex 16` |

- `CHAT_GATEWAY_API_KEY`를 비우면 API Key 인증은 끄고, JWT만 사용 가능.
- `ALLOWED_SYSTEM_IDS`를 비우면 모든 `system_id` 허용.
- **`ALLOWED_CHAT_TOKEN_ORIGINS`**: `/v1/chat-token` 호출 허용 Origin (쉼표 구분). DrillQuiz 프론트 주소 예: `http://localhost:8080`. 비우면 모든 Origin 허용.

**한 번에 생성하기** (CHAT_GATEWAY_JWT_SECRET, CHAT_GATEWAY_API_KEY만 자동 생성):

```bash
./scripts/gen-env-values.sh
```

출력된 줄을 `.env`에 복사한 뒤, `DIFY_API_KEY`는 Dify **API 액세스**에서 복사해 넣으면 됩니다.

### 프론트에서 채팅 토큰 API로 발급 (DrillQuiz 등)

JWT를 수동으로 발급하지 않고, 프론트에서 **API로 토큰 발급**할 수 있음.

- **GET /v1/chat-token**: 쿼리 `system_id`, `user_id`(필수), 선택 `lang`(en|es|ko|zh|ja). 헤더 **X-API-Key**. 응답 `{ "token": "<JWT>" }` (24시간 유효). `lang` 있으면 `{ "token": "...", "ui": { "title", "close", "open", "tokenError", "loading" } }` 로 위젯 셸 다국어 문구 포함(채팅 앱 다국어는 chat-gateway 담당).
- DrillQuiz .env: `VUE_APP_CHAT_GATEWAY_URL`, **VUE_APP_CHAT_GATEWAY_API_KEY** (chat-gateway `CHAT_GATEWAY_API_KEY`와 동일). 선택: `VUE_APP_CHAT_GATEWAY_SYSTEM_ID=drillquiz`. **user_id**는 앱에서 결정: 로그인 시 **username**, 비로그인 시 **anonymous**. **언어**: 위젯이 iframe URL에 `lang=en|es|ko|zh|ja`를 붙여 전달하며, 넘어오지 않으면 채팅 페이지에서 브라우저 언어로 폴백. Dify로 전송 시 `inputs.language`로 전달됨(워크플로에 변수 있으면 사용).
- chat-gateway .env에 **ALLOWED_CHAT_TOKEN_ORIGINS=http://localhost:8080** 등 호출 허용 Origin을 넣으면, 해당 Origin에서만 `/v1/chat-token` 호출 가능.

### JWT 발급 (대상 시스템에서, 수동)

대상 시스템이 채팅 페이지로 보낼 때 사용할 JWT 예시 (HS256):

- Payload: `{"system_id": "drillquiz", "user_id": "12345", "exp": <만료시간>}`  
- 서명: `CHAT_GATEWAY_JWT_SECRET` 으로 서명.  
- 게이트웨이 `/chat?token=<jwt>` 로 리다이렉트하면, 게이트웨이가 검증 후 채팅 페이지를 띄움.

---

## 대화 내용 SQLite 저장

- **채팅 시 바로 기록**: **POST /v1/chat**으로 메시지를 보내면, Dify 응답을 받은 직후 **conversation_cache**, **message_cache**에 곧바로 저장합니다. 별도 sync 단계 없이 DB에 남습니다.
- **POST /v1/sync** (헤더 `X-API-Key` 필요): 등록된 (system_id, user_id)마다 Dify **Service API**로 대화 목록·메시지를 조회해 캐시에 보강(upsert). 기존 대화나 다른 경로로 쌓인 데이터 정리용.
- **동기화 대상**: `ConversationMapping`(POST /v1/chat 사용 이력) + **SyncUser**(/chat·/chat-api 접속 시 자동 등록).

- **주기 실행 예**: cron에서 `curl -X POST http://localhost:8088/v1/sync -H "X-API-Key: YOUR_KEY"` 를 5분마다 호출.

---

## 아키텍처

```
[DrillQuiz / CoinTutor / ...] → [Chat Gateway] → Dify API
                                      ↓
                               SQLite (conversation 매핑 + conversation_cache, message_cache)
```

- 새 서비스 추가: 게이트웨이에 API Key 발급(또는 동일 CHAT_GATEWAY_JWT_SECRET + system_id 규칙)만 하면 되며, 대상 시스템 코드에 Dify 호출 로직을 넣을 필요 없음.

---

## 프로젝트 구조

```
chat-gateway/
├── README.md
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py          # FastAPI 앱, 라우터 등록
│   ├── config.py        # 환경변수 설정
│   ├── auth.py          # API Key / JWT 검증
│   ├── database.py      # SQLAlchemy 비동기 엔진, 세션
│   ├── models.py        # ConversationMapping, ConversationCache, MessageCache
│   ├── sync_service.py  # Dify → SQLite 동기화
│   ├── schemas.py       # 요청/응답 Pydantic 모델
│   ├── dify_client.py   # Dify API 호출
│   ├── templates.py     # Jinja2 템플릿 엔진
│   └── routers/
│       ├── chat.py      # POST/GET /v1/chat, /v1/conversations, ...
│       └── chat_page.py # GET /chat?token=<JWT>
└── templates/
    └── chat_api.html    # 채팅 페이지 (대화 목록·메시지·전송, DB 기록)
```
