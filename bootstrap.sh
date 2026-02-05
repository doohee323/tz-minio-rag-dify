#!/usr/bin/env bash
# Demo app environment bootstrap (see docs/rag-multi-topic.md, docs/rag-requirements-and-plan.md)
# Prerequisites: K8s cluster exists, kubectl/kubeconfig configured
# Order: Ingress NGINX → MinIO → RAG → Dify (skip if already installed)

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TZ_REPO_ROOT="${REPO_ROOT}"

# Use KUBECONFIG if set, otherwise default
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"

echo "=============================================="
echo " RAG + Dify demo environment bootstrap"
echo " REPO_ROOT=${REPO_ROOT}"
echo " KUBECONFIG=${KUBECONFIG}"
echo "=============================================="

# Phase 0: Pre-check (docs/rag-requirements-and-plan.md Phase 0)
phase0() {
  echo ""
  echo "[Phase 0] K8s access check"
  if ! kubectl get nodes &>/dev/null; then
    echo "Error: kubectl get nodes failed. Check KUBECONFIG or cluster."
    exit 1
  fi
  kubectl get nodes
  echo ""
}

# 1. Ingress NGINX (TLS/HTTP routing — entry point for all services)
install_ingress() {
  echo ""
  echo "[1/5] Install Ingress NGINX (cert-manager, TLS)"
  if helm list -n default 2>/dev/null | grep -q ingress-nginx; then
    echo "  → Already installed, skipping"
    return 0
  fi
  (cd "${REPO_ROOT}/ingress_nginx" && bash install.sh)
}

# 2. MinIO (object store, rag-docs bucket — Phase 1)
install_minio() {
  echo ""
  echo "[2/5] Install MinIO (namespace: devops)"
  if helm list -n devops 2>/dev/null | grep -q minio; then
    echo "  → Already installed, skipping"
    return 0
  fi
  (cd "${REPO_ROOT}/minio" && bash install.sh)
}

# 3. RAG stack (Qdrant, collections, Backend/Frontend, Ingestion, Ingress) — Dify excluded
install_rag() {
  echo ""
  echo "[3/5] Install RAG stack (namespace: rag, CoinTutor + DrillQuiz)"
  if kubectl get ns rag &>/dev/null && helm list -n rag 2>/dev/null | grep -q qdrant; then
    echo "  → Already installed, skipping"
    return 0
  fi
  (cd "${REPO_ROOT}/rag" && bash install.sh)
}

# 4. Dify (chatbot, RAG tool integration)
install_dify() {
  echo ""
  echo "[4/5] Install Dify (namespace: dify)"
  if helm list -n dify 2>/dev/null | grep -q dify; then
    echo "  → Already installed, skipping"
    return 0
  fi
  (cd "${REPO_ROOT}/dify" && bash install.sh)
}

summary() {
  echo ""
  echo "=============================================="
  echo " Bootstrap complete"
  echo "=============================================="
  echo "  Ingress:  NGINX + cert-manager (default NS)"
  echo "  MinIO:    devops NS; create rag-docs bucket via console or minio-bucket-job"
  echo "  RAG:      rag NS, Qdrant, rag-backend, rag-backend-drillquiz, CronJob"
  echo "  Dify:     dify NS (configure tool URLs in Web UI for RAG)"
  echo ""
  echo "  Note: Without rag-ingestion-secret-cointutor and rag-ingestion-secret-drillquiz, RAG Backend Pods will fail."
  echo "        See rag/README.md and docs/rag-multi-topic.md checklist."
  echo "=============================================="
}

# --- Uninstall: Dify + RAG only (MinIO / Ingress not supported) ---
uninstall_dify_rag() {
  echo ""
  echo "[1/1] Remove Dify + RAG stack (rag/uninstall.sh)"
  (cd "${REPO_ROOT}/rag" && bash uninstall.sh)
}

uninstall_summary() {
  echo ""
  echo "=============================================="
  echo " Uninstall complete (Dify + RAG removed)"
  echo "=============================================="
  echo "  Reinstall: ./bootstrap.sh"
  echo "=============================================="
}

# Run
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
