# DrillQuiz + Dify 채팅 연동: 사용자 정보 전달·추적·F/U

Chatbot URL 예: `https://dify.drillquiz.com/chatbot/5J5xj0G2GHxEglrL`  
DrillQuiz 사이트에서 **iframe/embed** 또는 **API 대리 호출**로 채팅을 제공할 때, **DrillQuiz 사용자 정보를 어떻게 넘기고, 추적·F/U하는지** 정리.

---

## 1. Dify에서 사용자 구분 방식

- **Service API(채팅 API)** 에서는 **`user` 쿼리 파라미터**가 **사용자 식별자**입니다.
- 같은 `user` 값으로 생성된 대화만 묶어서 조회·관리할 수 있습니다.
- 참고: [Dify API - Get Conversations](https://docs.dify.ai/api-reference/conversations/get-conversations) — `user`(필수), `Authorization: Bearer app-xxx`

**정리**: DrillQuiz 사용자 ID(예: `drillquiz_user_12345`)를 Dify API 호출 시 `user` 파라미터로 넘기면, "누가 어떤 대화를 했는지" 추적·조회 가능.

---

## 2. 채팅 제공 방식별로 사용자 정보 넣는 방법

### A. DrillQuiz 사이트에 Dify Chatbot **embed**

- DrillQuiz 웹에 **채팅 위젯(embed)** 을 넣고, **로그인한 사용자 정보**를 설정한 뒤 스크립트 로드.

```html
<script>
  window.difyChatbotConfig = {
    token: 'app-5J5xj0G2GHxEglrL',  // 실제 토큰은 앱 발급 값으로
    baseUrl: 'https://dify.drillquiz.com',
    // DrillQuiz 로그인 사용자 ID → Dify user 식별자로 전달
    inputs: {
      user_id: 'drillquiz_12345',   // 서버에서 렌더 시 주입
      email: 'user@example.com'    // 선택
    }
  };
</script>
<script src="https://dify.drillquiz.com/embed.min.js" defer></script>
```

- `inputs` 에 넣은 값은 **워크플로 변수**로 쓰일 수 있음.  
- **Dify Chat/API가 `user` 를 어디서 채우는지**는 embed 스크립트/문서 확인이 필요.  
  - **embed가 `inputs.user_id` 를 API의 `user` 로 보내는지** 확인 후, 안 되면 아래 B처럼 **DrillQuiz 백엔드 대리 호출**로 `user` 를 반드시 넣는 편이 안전합니다.

### B. DrillQuiz 백엔드가 Dify API를 **대리 호출** (가장 확실)

- 사용자는 **DrillQuiz 웹/앱**에서만 로그인. 채팅 요청은 **DrillQuiz 백엔드**로 보냄.
- DrillQuiz 백엔드가 **Dify Service API** 로 메시지 전송 시 **매 요청에 `user` = DrillQuiz 사용자 ID** 를 넣음.

```
[사용자] → DrillQuiz 프론트 → DrillQuiz 백엔드 → Dify API (user=drillquiz_user_12345)
```

- 이렇게 하면 §4(인증), §5(추적), §6(F/U) 모두 **DrillQuiz가 주도**할 수 있음.
- Dify API 예시 (채팅 메시지 전송):
  - `POST /v1/chat-messages`  
  - Query: `user=drillquiz_user_12345`  
  - Body: `inputs`, `query`, `conversation_id` 등 (Dify API 문서 참고)

- **단점**: 채팅을 붙일 때마다 **대상 시스템(DrillQuiz, CoinTutor 등) 쪽에** Dify API 호출·user 매핑 로직을 넣어야 함.

---

## 3. 채팅 쪽에서 사용자·대화를 관리하는 방법 (대상 시스템 수정 최소화)

**목표**: 새 서비스에 채팅을 붙일 때 **대상 시스템은 최소한만 수정**하고, **사용자 정보·대화 내용·F/U는 채팅 앱(또는 별도 API) 한 곳에서 관리**하는 방식.

**embed/iframe과의 관계**  
- Dify의 **iframe/embed를 아예 못 쓰는 것은 아님**.  
- 다만 “사용자·대화를 **채팅 쪽에서 일괄 관리**”하려면, embed만으로는 **부족**함.  
  - embed를 **각 시스템 페이지에 직접** 넣으면, 사용자 식별·대화 목록·F/U는 여전히 각 시스템 또는 Dify에 흩어지고, 새 서비스마다 해당 시스템에 설정/코드가 필요함.  
- **게이트웨이**를 두면 **embed는 그대로 활용 가능**.  
  - 게이트웨이가 “embed를 로드하는 채팅 페이지”를 제공하고, 대상 시스템은 그 페이지로 이동만 시켜 주면 됨(§3.1 옵션 1·2).  
- **정리**: 요구사항(중앙 관리)을 만족하려면 **게이트웨이(또는 별도 웹앱)** 가 필요하고, 그 위에서 **embed 사용 여부는 선택**임.

### 3.1 공통 채팅 게이트웨이 API + 웹앱 (권장)

**구성**: Dify 앞단에 **채팅 전용 API 서버(및 필요 시 채팅용 웹앱)** 를 둠.

```
[대상 시스템 A/B/C] → [채팅 게이트웨이 API] → Dify API
                            ↓
                     (자체 DB: 사용자·대화 매핑, 로그)
```

- **게이트웨이 API**가 할 일:
  1. **통일된 채팅 API** 제공  
     - 예: `POST /v1/chat` — Body 또는 Header: `system_id`(예: drillquiz, cointutor), `user_id`(대상 시스템 사용자 ID), `message`, (선택) `conversation_id`.  
     - 게이트웨이가 내부적으로 Dify `user` 값을 `{system_id}_{user_id}` 로 생성해 Dify API 호출. Dify API 키는 게이트웨이만 보유.
  2. **사용자·대화 관리**  
     - 자체 DB에 `(system_id, user_id)` ↔ `conversation_id`, 타임스탬프, (선택) 메시지 요약 저장.  
     - 조회 API: `GET /v1/conversations?system_id=drillquiz&user_id=12345` → 해당 사용자 대화 목록. `GET /v1/conversations/:id/messages` → 대화 내용(필요 시 Dify API 결과 캐시 또는 동기화).
  3. **인증**  
     - 대상 시스템이 **API 키** 또는 **서명된 토큰(JWT)** 으로 게이트웨이를 호출. 게이트웨이는 토큰에서 `system_id`, `user_id` 추출.  
     - 새 서비스 추가 = 게이트웨이에 `system_id` 등록 + API 키(또는 서명 키) 발급만 하면 됨. **대상 시스템 코드에는 Dify 직접 호출 로직 없음.**

- **채팅 UI 제공** (선택):
  - **옵션 1**: 게이트웨이가 **채팅 창 페이지**를 제공. 대상 시스템은 "채팅 열기" 시 `https://chat-gateway.example.com/chat?token=<JWT>` 로 리다이렉트. JWT에 `system_id`, `user_id`, 만료 시간 포함. 게이트웨이가 토큰 검증 후 Dify embed 또는 자체 UI로 채팅 (내부적으로는 위 API로 Dify 호출).
  - **옵션 2**: 대상 시스템은 계속 embed를 쓰되, **embed가 로드되는 페이지**를 게이트웨이에서 제공. 해당 페이지 진입 시 토큰으로 사용자 확인 후 `difyChatbotConfig.inputs` 또는 API 호출 시 `user` 주입.

- **효과**  
  - 사용자 정보·대화 이력·통계·F/U를 **채팅 게이트웨이(및 자체 DB)** 에서 일괄 관리.  
  - DrillQuiz, CoinTutor 등 **대상 시스템은** "게이트웨이 API 호출" 또는 "게이트웨이 채팅 URL로 이동"만 하면 되어, **채팅 붙일 때마다 각 시스템을 크게 수정할 필요 없음.**

### 3.2 필요한 API (게이트웨이 설계 예시)

| API | 용도 |
|-----|------|
| `POST /v1/chat` | 메시지 전송. Body/Header: `system_id`, `user_id`, `message`, (선택) `conversation_id`. 게이트웨이가 Dify 호출 + 자체 DB에 대화 매핑 저장. |
| `GET /v1/conversations` | `system_id`, `user_id` 로 해당 사용자 대화 목록 조회 (게이트웨이 DB 또는 Dify API `GET /conversations?user=xxx` 조합). |
| `GET /v1/conversations/:id/messages` | 특정 대화 메시지 목록 (Dify API 또는 게이트웨이 캐시). |
| `GET /v1/chat` (또는 채팅 페이지) | JWT로 사용자 확인 후 채팅 UI 제공. 토큰에 `system_id`, `user_id` 포함. |

- **별도 웹앱**으로 둘 경우: 위 API를 제공하는 백엔드 + "채팅 창" 프론트(리다이렉트용 또는 embed 호스팅)를 하나의 서비스로 배포하면 됨.

---

## 4. §4·§5·§6 구현 시 무엇을 하면 되는지

| 목표 | 어떻게 하면 되는지 |
|------|---------------------|
| **§4 iframe/embed 인증** | (A) embed: DrillQuiz 페이지는 로그인 사용자에게만 노출. (B) API 대리 호출: 해당 백엔드가 세션 검증 후 Dify 호출. **(3.1 게이트웨이)** 게이트웨이가 토큰 검증 후 채팅/API 제공. |
| **§5 사용자·요청 추적** | **`user` = (system_id + user_id)** 로 통일. 게이트웨이 사용 시 게이트웨이 DB + Dify API로 대화 목록·통계 일괄 조회. |
| **§6 채팅 F/U** | 게이트웨이 DB에 (system_id, user_id) ↔ conversation_id 저장. 상담/관리 화면은 게이트웨이 API로 "사용자별 대화 목록·메시지" 조회 후 티켓/이슈 연동. |

---

## 5. 사용자 정보 "추출·관리" 요약

- **추출**: Dify(또는 게이트웨이)에 넘기는 값은 **대상 시스템 + 사용자 식별자** (예: `drillquiz_12345`) 로 통일.  
  - (A) embed: 서버 렌더 시 `inputs.user_id` 등으로 주입.  
  - (B) API 대리 호출: 해당 백엔드가 세션에서 사용자 ID 읽어 `user` 로 전달.  
  - **(3.1 게이트웨이)**: 대상 시스템은 `system_id` + `user_id`(또는 JWT)만 넘기면, 게이트웨이가 `user` 생성·Dify 호출·DB 저장까지 처리.
- **관리**:
  - **게이트웨이 사용 시**: 사용자·대화·통계는 **게이트웨이 DB + API**에서 관리. 대상 시스템은 게이트웨이 API만 호출하면 됨.
  - **게이트웨이 없이 (A)(B)만 쓸 때**: 해당 시스템 DB에 `user_id` ↔ `conversation_id` 저장 후, Dify API로 `GET /conversations?user=xxx` 조회·동기화.

**정리**: 채팅을 붙일 때마다 대상 시스템을 수정하지 않으려면 **공통 채팅 게이트웨이 API(및 필요 시 채팅용 웹앱)** 를 두고, 사용자 정보·대화 내용·F/U를 **채팅 쪽(게이트웨이)** 에서 관리하는 방식(§3.1)을 쓰면 됩니다.
