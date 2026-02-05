#!/usr/bin/env bash
# 데모 앱 환경 부트스트랩 (docs/rag-multi-topic.md, docs/rag-requirements-and-plan.md 기준)
# 전제: K8s 클러스터 존재, kubectl/kubeconfig 설정됨
# 순서: Ingress NGINX → MinIO → RAG → Dify (이미 있으면 스킵)

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TZ_REPO_ROOT="${REPO_ROOT}"

# KUBECONFIG는 있으면 사용, 없으면 기본
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"

echo "=============================================="
echo " RAG + Dify 데모 환경 부트스트랩"
echo " REPO_ROOT=${REPO_ROOT}"
echo " KUBECONFIG=${KUBECONFIG}"
echo "=============================================="

# Phase 0: 사전 확인 (docs/rag-requirements-and-plan.md Phase 0)
phase0() {
  echo ""
  echo "[Phase 0] K8s 접근 확인"
  if ! kubectl get nodes &>/dev/null; then
    echo "오류: kubectl get nodes 실패. KUBECONFIG 또는 클러스터를 확인하세요."
    exit 1
  fi
  kubectl get nodes
  echo ""
}

# 1. Ingress NGINX (TLS/HTTP 라우팅 — 모든 서비스 진입점)
install_ingress() {
  echo ""
  echo "[1/5] Ingress NGINX 설치 (cert-manager, TLS)"
  if helm list -n default 2>/dev/null | grep -q ingress-nginx; then
    echo "  → 이미 설치됨, 스킵"
    return 0
  fi
  (cd "${REPO_ROOT}/ingress_nginx" && bash install.sh)
}

# 2. MinIO (객체 저장소, rag-docs 버킷 규칙 — Phase 1)
install_minio() {
  echo ""
  echo "[2/5] MinIO 설치 (namespace: devops)"
  if helm list -n devops 2>/dev/null | grep -q minio; then
    echo "  → 이미 설치됨, 스킵"
    return 0
  fi
  (cd "${REPO_ROOT}/minio" && bash install.sh)
}

# 3. RAG 스택 (Qdrant, 컬렉션, Backend/Frontend, Ingestion, Ingress) — Dify 제외
install_rag() {
  echo ""
  echo "[3/5] RAG 스택 설치 (namespace: rag, CoinTutor + DrillQuiz)"
  if kubectl get ns rag &>/dev/null && helm list -n rag 2>/dev/null | grep -q qdrant; then
    echo "  → 이미 설치됨, 스킵"
    return 0
  fi
  (cd "${REPO_ROOT}/rag" && bash install.sh)
}

# 4. Dify (챗봇, RAG 도구 연동)
install_dify() {
  echo ""
  echo "[4/5] Dify 설치 (namespace: dify)"
  if helm list -n dify 2>/dev/null | grep -q dify; then
    echo "  → 이미 설치됨, 스킵"
    return 0
  fi
  (cd "${REPO_ROOT}/dify" && bash install.sh)
}

summary() {
  echo ""
  echo "=============================================="
  echo " 부트스트랩 완료"
  echo "=============================================="
  echo "  Ingress:  NGINX + cert-manager (default NS)"
  echo "  MinIO:    devops NS, rag-docs 버킷은 콘솔 또는 minio-bucket-job으로 생성"
  echo "  RAG:      rag NS, Qdrant, rag-backend, rag-backend-drillquiz, CronJob"
  echo "  Dify:     dify NS (RAG 연동 시 Web UI에서 도구 URL 설정)"
  echo ""
  echo "  참고: rag-ingestion-secret 없으면 RAG Backend Pod이 실패합니다."
  echo "        rag/README.md, docs/rag-multi-topic.md 체크리스트 참고."
  echo "=============================================="
}

# --- Uninstall: Dify + RAG만 제거 (MinIO / Ingress는 미지원) ---
uninstall_dify_rag() {
  echo ""
  echo "[1/1] Dify + RAG 스택 삭제 (rag/uninstall.sh)"
  (cd "${REPO_ROOT}/rag" && bash uninstall.sh)
}

uninstall_summary() {
  echo ""
  echo "=============================================="
  echo " Uninstall 완료 (Dify + RAG만 제거)"
  echo "=============================================="
  echo "  재설치: ./bootstrap.sh"
  echo "=============================================="
}

# 실행
main() {
  phase0
  install_ingress
  install_minio
  install_rag
  install_dify
  summary
}

if [[ "${1:-}" == "uninstall" ]]; then
  phase0
  uninstall_dify_rag
  uninstall_summary
else
  main "$@"
fi
