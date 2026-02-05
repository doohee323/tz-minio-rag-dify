# Chat 모듈 적용 방법 (Vue 앱)

tz-drillquiz에 적용한 채팅 위젯을 다른 Vue 프로젝트에 붙이는 방법을 정리한 문서입니다.

## 전제 조건

- **Chat Gateway** 서버가 배포되어 있고, `CHAT_GATEWAY_API_KEYS` 중 하나의 API 키를 알고 있어야 합니다.
- Vue 2/3 프로젝트에서 **인증 서비스**가 있거나, 최소 인터페이스(authService adapter)를 구현할 수 있어야 합니다.

---

## 1. 파일 복사

| 소스 (sample) | 대상 (프로젝트) |
|---------------|-----------------|
| `sample/ChatWidget.vue` | `src/components/ChatWidget.vue` |

```bash
cp chat-gateway/sample/ChatWidget.vue your-vue-app/src/components/ChatWidget.vue
```

---

## 2. 인증 서비스(authService) 연동

ChatWidget은 다음 인터페이스를 사용합니다.

- **`authService.getUserSync()`**  
  - 반환: `{ username: string }` 또는 `null`  
  - 로그인 사용자: `username`(또는 사용자 식별자) 반환  
  - 비로그인: `null` → 위젯에서는 `user_id`를 `anonymous`로 전달

- **`authService.subscribe(handler)`**  
  - 인증 상태 변경 시 호출될 콜백 등록  
  - 반환: 구독 해제 함수 (컴포넌트 제거 시 호출)

### 2-1. 이미 authService가 있는 경우

- `getUserSync()`가 `{ username }` 형태를 반환하도록 하거나,
- ChatWidget 내부 `getChatUserId()`에서 사용하는 필드(id, email 등)를 프로젝트에 맞게 한 곳만 수정해도 됩니다.

### 2-2. authService가 없는 경우

- `sample/authService.adapter.example.js`를 `src/services/authService.js`로 복사한 뒤,
- 로그인/로그아웃 시 `setAuthUser(user)` 또는 `setAuthUser(null)`를 호출하도록 연동합니다.

---

## 3. App.vue 수정

- **import**: `ChatWidget` 컴포넌트 추가
- **components**: `ChatWidget` 등록
- **template**: 레이아웃 하단(예: Footer 다음)에 `<ChatWidget />` 한 줄 추가

자세한 코드 조각은 `App.vue.snippet` 참고.

```vue
<template>
  <div id="app">
    <!-- ... 기존 레이아웃 ... -->
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

## 4. 환경 변수

빌드 시 다음 환경 변수가 필요합니다. 로컬은 `.env`, CI는 `env-frontend` 등에서 플레이스홀더 치환.

| 변수 | 설명 | 예시 |
|------|------|------|
| `VUE_APP_CHAT_GATEWAY_URL` | Chat Gateway 기준 URL (끝에 `/` 없음) | `https://chat.drillquiz.com` |
| `VUE_APP_CHAT_GATEWAY_API_KEY` | 게이트웨이 API 키 (CHAT_GATEWAY_API_KEYS 중 하나) | (Jenkins/CI에서 주입) |
| `VUE_APP_CHAT_GATEWAY_SYSTEM_ID` | 시스템 식별자 (게이트웨이 ALLOWED_SYSTEM_IDS와 일치) | `drillquiz` |

예시 파일: `env-frontend.example`

---

## 5. 다국어(i18n) (선택)

- 앱에서 `vue-i18n`을 쓰고 있다면 `this.$i18n.locale`이 있으면 위젯이 그 값을 `lang` 파라미터로 넘깁니다.
- 지원 언어: `en`, `es`, `ko`, `zh`, `ja` (gateway 채팅 UI/응답 언어에 사용).

---

## 6. CI에서 빌드 시 (예: Jenkins)

- 브랜치별로 Chat Gateway 도메인/API 키를 다르게 쓰는 경우:
  - `env-frontend`에 `VUE_APP_CHAT_GATEWAY_URL=https://CHAT_GATEWAY_DOMAIN_PLACEHOLDER`,  
    `VUE_APP_CHAT_GATEWAY_API_KEY=CHAT_GATEWAY_API_KEY_PLACEHOLDER` 로 두고,
  - 빌드 스크립트에서 `CHAT_GATEWAY_DOMAIN_PLACEHOLDER` → `chat.drillquiz.com`(운영) / `chat-qa.drillquiz.com`(QA) 등으로,
  - `CHAT_GATEWAY_API_KEY_PLACEHOLDER` → Jenkins 자격 증명 등에서 가져온 API 키로 치환하면 됩니다.

---

## 7. 동작 요약

1. 사용자가 우측 하단 채팅 버튼을 누르면,
2. `GET /v1/chat-token?system_id=...&user_id=...&lang=...` 를 `X-API-Key`로 호출해 JWT 토큰을 받고,
3. `채팅 URL?token=...&embed=1&lang=...` 로 iframe을 띄웁니다.
4. 로그인 사용자는 `user_id`가 `username`, 비로그인은 `anonymous`로 전달됩니다.

---

## sample 폴더 구성

| 파일 | 용도 |
|------|------|
| `ChatWidget.vue` | 위젯 컴포넌트 (복사해 사용) |
| `App.vue.snippet` | App.vue에 넣을 import/등록/템플릿 조각 |
| `env-frontend.example` | 프론트 빌드용 env 예시 |
| `authService.adapter.example.js` | authService가 없을 때 최소 구현 예시 |
| `INTEGRATION.md` | 본 적용 방법 문서 |
