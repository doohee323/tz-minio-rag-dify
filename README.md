# tz-minio-rag-dify

Kubernetes 위에서 **RAG(Retrieval-Augmented Generation)** 와 **Dify 챗봇** 데모 환경을 구성하는 리포지터리입니다. Ingress NGINX, MinIO, Qdrant, 주제별 RAG 백엔드(CoinTutor / DrillQuiz), Dify를 순서대로 설치합니다.

## 사용 방법

**전제**: Kubernetes 클러스터와 `kubectl`(또는 `KUBECONFIG`)이 준비되어 있어야 합니다.

```bash
# 필요 시 KUBECONFIG 지정
export KUBECONFIG=~/.kube/your-config

# 한 번에 설치 (이미 있는 컴포넌트는 스킵)
./bootstrap.sh
```

설치 순서: **Ingress NGINX** → **MinIO** → **RAG 스택** → **Dify**.  
설치 후 RAG Backend가 기동하려면 `rag-ingestion-secret-cointutor`, `rag-ingestion-secret-drillquiz`(MinIO·Gemini 등)를 생성해야 합니다. 자세한 절차와 체크리스트는 `rag/README.md`, `docs/rag-multi-topic.md`를 참고하세요.

## 문서

- `docs/rag-multi-topic.md` — 주제별 RAG 분리(CoinTutor/DrillQuiz), MinIO 경로, Dify 도구 URL
- `docs/rag-requirements-and-plan.md` — 요구사항 및 Phase별 수행 계획
- `docs/additional-requirements.md` — 스케일·통제·트래픽·iframe 인증·추적·F/U 등 추가 요구사항 및 운영 고려사항
- `docs/dify-drillquiz-embed-and-tracking.md` — DrillQuiz + Dify 채팅 연동 시 사용자 정보 전달·추적·F/U (embed / API 대리 호출)
