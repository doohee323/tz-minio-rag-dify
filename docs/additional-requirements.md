# 추가 요구사항 및 운영 고려사항

RAG + Dify 데모 환경의 확장·운영·보안·추적을 위한 요구사항 정리.

---

## 1. 사용자 채팅 증가 시 Scale 관리

| 대상 | 설명 | 대응 방향 |
|------|------|------------|
| **Dify API / Worker** | 채팅 요청 처리, 워크플로 실행. 동시 요청이 많으면 지연·타임아웃 | Helm values에서 `api.replicas`, `worker.replicas` 증가. HPA(CPU/메모리 기반) 적용. |
| **Dify Queue (Celery/Redis)** | 작업 큐 적체 시 대기 시간 증가 | Redis 리소스·복제, Worker 수 확장. 모니터링으로 큐 깊이 확인. |
| **RAG Backend** | `/query` 동시 호출 증가 시 Qdrant·임베딩 API 병목 | Deployment `replicas` 증가, Service 앞에 부하 분산. HPA 적용. |
| **Qdrant** | 벡터 검색 부하, 메모리 사용량 | Qdrant Helm 리소스 상향, 필요 시 수평 확장(클러스터 모드) 또는 전용 노드. |
| **임베딩 API (Gemini 등)** | 호출당 Quota·Rate limit | 배치/캐시 전략, 또는 여러 API 키 로테이션. Dify 측 요청 제한과 병행. |
| **MinIO** | 대용량 파일 업로드/다운로드 | 스토리지 용량·IO, 필요 시 MinIO 분산 구성. |

**현재 리포지터리 상태**: **기본 설치 시 HPA 적용됨 (min=1, max=1)**. RAG는 `rag/rag-hpa.yaml`로 rag-backend, rag-backend-drillquiz, rag-frontend에 HPA 적용(install.sh [5b/7]). Dify는 `dify/dify-hpa.yaml`로 dify-api, dify-worker에 HPA 적용(install.sh [5b/5]). 모두 minReplicas=1, maxReplicas=1이라 당장은 replica 1개 유지되며, 채팅 증가 시 `kubectl edit hpa ... -n rag` 등으로 maxReplicas만 올리면 자동 확장됨.

**확장 시 (maxReplicas 상향)**

- **RAG**: HPA가 이미 있으므로 `kubectl edit hpa rag-backend -n rag`에서 `maxReplicas`를 2 이상으로 변경. 또는 `kubectl patch hpa rag-backend -n rag -p '{"spec":{"maxReplicas":5}}'`
- **Dify**: `kubectl edit hpa dify-api -n dify`, `kubectl edit hpa dify-worker -n dify`에서 `maxReplicas` 상향.
- **메트릭 서버**: HPA가 CPU 기준으로 동작하려면 클러스터에 metrics-server 설치 필요. 미설치 시 `kubectl top pods`가 동작하지 않으며, HPA는 현재 replica를 유지만 함.
- **Qdrant**: 단일 노드 구성이 기본. 리소스 상향은 `qdrant-values.yaml`의 `resources` 수정. 수평 확장은 클러스터 모드 전환 필요.

**추가 고려**: 네트워크 대역폭, Ingress Controller 리소스, DB(PostgreSQL) 연결 수·풀. Dify는 DB 연결을 많이 쓰므로 API replica 수와 DB `max_connections`를 맞춰야 함.

---

## 2. 불필요한 정보를 요구하는 사용자 통제

| 수단 | 설명 |
|------|------|
| **시스템 프롬프트** | Dify 워크플로의 LLM 노드에서 "개인정보·민감 정보를 묻지 말 것", "지식 범위 밖 질문은 거절" 등 규칙 명시. |
| **입력 검증** | 커스텀 도구 또는 워크플로 앞단에서 키워드/패턴 필터(예: 주민번호, 이메일 정규식)로 차단·대체. |
| **정책 노드** | Dify에서 조건 분기로 "질문 분류" 후 허용 주제만 RAG/LLM으로 전달, 그 외는 고정 안내 메시지. |
| **사용 약관·가이드** | 채팅 진입 전 또는 첫 화면에 "질문은 서비스 범위 내에서만" 등 안내. 위반 시 이용 제한 정책과 연동. |
| **관리자 모니터링** | 이상 질문 패턴·빈도 감지 시 알림·수동 제재(블랙리스트, 세션 차단). (5번 추적과 연계) |

**추가 고려**: Dify 자체에는 "역할 기반 접근"이 있으나, 질문 내용 단위의 정책 엔진은 워크플로·외부 서비스로 구현해야 함. 민감 정보 마스킹은 로그/저장 단계에서도 적용 권장.

---

## 3. 트래픽 양 통제

| 계층 | 방법 | 적용 여부 |
|------|------|------------|
| **Ingress / LB** | Nginx Ingress `limit-rps`, `limit-connections` 등으로 RPS·동시 접속 제한. | ✅ **적용**: `rag-ingress.yaml`에 `limit-rps: "30"`, `limit-connections: "20"` (IP당, 초과 시 503). |
| **Dify** | 앱별/사용자별 호출 제한이 있다면 Dify 설정 활용. API 키 단위 제한. | ⚪ Dify Web UI/앱 설정에서 수동 구성. |
| **RAG Backend** | IP별 rate limit (slowapi 등). | ✅ **적용**: `/query`에 slowapi `20/minute` (환경 변수 `RATE_LIMIT_QUERY`로 변경 가능). |
| **K8s** | ResourceQuota로 네임스페이스별 상한. | ✅ **적용**: `rag-resource-quota.yaml` (rag NS: CPU/메모리·Pod 상한), install.sh [5c/7]. |
| **외부 API** | Gemini 등 할당량·모니터링·알림. | ⚪ 사용량 모니터링·알림은 운영에서 구성. |

**추가 고려**: DDoS/비정상 트래픽은 WAF·Cloud LB 레벨에서 처리하는 것이 좋음.

---

## 4. Dify 채팅창을 iframe으로 제공할 때 인증

| 방식 | 설명 |
|------|------|
| **Dify API Key (앱별)** | Dify에서 앱별 API 키 발급. iframe 부모 페이지에서 사용자 로그인 후, 백엔드가 Dify API 키를 사용자 세션과 매핑해 전달. 채팅 요청은 부모 도메인 백엔드 경유로 키 노출 최소화. |
| **SSO / OAuth** | Dify Enterprise 등 SSO 지원 시, iframe 진입 전 부모 사이트에서 SSO 로그인 → 토큰 전달. Community 버전은 제한적이므로, 부모 사이트 인증 후 "Dify 사용 권한이 있는 사용자"만 iframe URL 노출. |
| **부모 도메인 인증** | 사용자는 부모 사이트에서만 로그인. iframe의 `src`를 인증된 사용자에게만 동적으로 부여(예: 쿼리/토큰 포함 임시 URL). Dify는 가능하면 내부용으로 두고, 부모가 프록시하거나 CORS/쿠키 정책으로 제한. |
| **토큰 전달** | 부모 페이지가 로그인 세션/토큰을 쿼리 또는 postMessage로 iframe에 전달. iframe 내 채팅 클라이언트가 해당 토큰을 Dify API 호출 시 헤더에 포함. (Dify가 사용자 토큰을 받는 방식이면) |
| **도메인·X-Frame-Options** | Dify/Ingress에서 `X-Frame-Options` 또는 CSP `frame-ancestors`를 부모 도메인만 허용하도록 설정해, 허용된 사이트에서만 iframe 임베드 가능하도록 제한. |

**추가 고려**: iframe과 부모 도메인이 다르면 쿠키 공유 제한(SameSite 등). Dify 채팅을 "부모 사이트 백엔드 → Dify API 대리 호출" 구조로 두면, 인증은 전적으로 부모가 담당하고 Dify는 서버 간 통신만 하게 할 수 있음. 이 경우 사용자별 권한·할당량은 부모 백엔드에서 관리.

---

## 5. 사용자·요청 추적 및 통계

| 항목 | 방법 |
|------|------|
| **Dify 로그** | API/Worker 로그에서 요청·앱 ID·사용자 식별자(설정된 경우) 수집. 로그 수집 파이프라인(예: Loki, ELK)으로 집계. |
| **앱별 API 키** | 사용자 또는 그룹별로 Dify 앱 API 키를 분리 발급하면, 로그/메트릭에서 키 단위로 요청 수·에러율 집계 가능. |
| **RAG Backend 로깅** | `/query` 호출 시 타임스탬프, collection, question 길이, 결과 수, 소요 시간, 클라이언트 식별자(헤더/API 키)를 로그 또는 DB에 기록. |
| **메트릭** | Prometheus 등으로 Dify API/Worker, RAG Backend, Qdrant 요청 수·지연 시간 수집. Grafana 대시보드로 "사용자/앱별 요청 수", "상위 질문" 등 통계. |
| **사용자 식별** | Dify에 사용자 정보를 넘기는 방식(예: API 파라미터, 메타데이터)이 있다면 동일 식별자를 로그·통계에 사용. iframe 연동 시 부모 사이트 사용자 ID를 Dify 호출 시 함께 전달하도록 설계. |

**추가 고려**: 개인정보 보호를 위해 로그 보존 기간·마스킹 정책을 두고, 통계는 가명/집계 위주로. "어떤 사용자가 어떤 요청을 했는지" 추적은 목적 명시·동의·최소 수집 원칙에 맞게 설계.

---

## 6. 사용자 채팅 F/U(후속 조치) 방법

| 수단 | 설명 |
|------|------|
| **대화 이력 저장** | Dify 대화 로그/DB 또는 부모 시스템에 대화 세션·메시지 저장. "미해결" 등 상태 플래그 두고, 담당자 배정·재접속 시 이어보기. |
| **티켓/이슈 연동** | 채팅 종료 시 "상담 요청" 버튼으로 기존 티켓 시스템(이슈 트래커, CRM)에 대화 요약·링크 생성. 담당자가 같은 문맥으로 F/U. |
| **사용자 식별 연동** | 로그인 사용자 ID와 대화를 매핑해 두면, "해당 사용자의 최근 대화" 조회로 F/U. Dify 앱 메타데이터나 API 파라미터로 user_id 전달. |
| **알림·큐** | "인간 개입 필요" 판단 시(예: 워크플로 분기) 웹훅·메일·슬랙으로 알림, 내부 큐에 넣어 담당자가 순서대로 F/U. |
| **대화 내보내기** | 사용자 또는 상담원이 대화를 PDF/텍스트로 내보내서 이메일·다른 채널로 전달 후 F/U. |

**추가 고려**: Dify 자체는 "채팅 F/U 전용" 기능이 제한적이므로, 부모 시스템(웹사이트 백엔드, CRM, 헬프데스크)에서 대화 이력·상태를 관리하고, Dify는 답변 생성만 담당하는 구조가 유리함. Dify API로 대화 이력 조회가 가능하다면 해당 API를 활용해 부모 시스템에 동기화.

---

## 7. 문서에서 도출한 추가 고려사항

| 영역 | 고려사항 |
|------|----------|
| **비용** | 임베딩·LLM API 호출 비용이 채팅량에 비례. 사용량·예산 알림, 상한 알림 설정. |
| **가용성** | Dify, RAG Backend, Qdrant, MinIO 중 일부 장애 시 장애 전파 최소화(회로 차단, fallback 메시지). |
| **백업·복구** | Dify DB(PostgreSQL), Qdrant 스냅샷, MinIO 버킷 백업 정책. 재해 복구 절차 정리. |
| **버전·배포** | Dify·RAG Backend 업데이트 시 호환성(API 스키마, 워크플로). Blue/Green 또는 카나리 배포로 위험 완화. |
| **규정 준수** | 로그·대화 저장 시 개인정보보호법·내부 보관 정책. 보존 기간·삭제 절차. |
| **다국어/접근성** | 채팅 UI·에러 메시지 다국어, 접근성(스크린 리더 등). iframe 제공 시 부모 사이트와 톤 통일. |

---

## 8. 체크리스트 (도입 시 참고)

- [ ] Scale: Dify API/Worker·RAG Backend replica·HPA, Qdrant·DB 리소스
- [ ] 통제: 시스템 프롬프트·입력 검증·정책 노드, 사용 약관
- [ ] 트래픽: Ingress rate limit, 앱/백엔드 rate limit, 외부 API 할당량 모니터링
- [ ] iframe 인증: 부모 사이트 인증·토큰 전달 방식, X-Frame-Options/CSP
- [ ] 추적/통계: 로그·메트릭 수집, 사용자/앱별 집계, 개인정보 정책
- [ ] F/U: 대화 저장·티켓 연동·사용자 매핑·알림
- [ ] 비용·가용성·백업·규정 준수
