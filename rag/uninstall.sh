#!/usr/bin/env bash
# Remove RAG stack + Dify (reverse order of install.sh)
# Usage: ./uninstall.sh
#   - Dify: remove Ingress, Helm, namespace dify
#   - RAG: remove Ingress, CronJob/Job, Backend/Frontend, Qdrant (Helm), namespace rag

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [[ -f /root/.bashrc ]]; then
  source /root/.bashrc
fi
function prop {
  key="${2}="
  file="/root/.k8s/${1}"
  if [[ ! -f "$file" ]]; then echo ""; return; fi
  rslt=$(grep "${3:-}" "$file" -A 10 | grep "$key" | head -n 1 | cut -d '=' -f2 | sed 's/ //g')
  [[ -z "$rslt" ]] && key="${2} = " && rslt=$(grep "${3:-}" "$file" -A 10 | grep "$key" | head -n 1 | cut -d '=' -f2 | sed 's/ //g')
  echo "$rslt" | tr -d '\n' | tr -d '\r'
}

KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"
alias k="kubectl --kubeconfig ${KUBECONFIG}"

k8s_project="${k8s_project:-$(prop 'project' 'project')}"
k8s_domain="${k8s_domain:-$(prop 'project' 'domain')}"
[[ -z "$k8s_project" ]] && k8s_project="rag"
[[ -z "$k8s_domain" ]] && k8s_domain="drillquiz.com"

NS=rag
NS_DIFY=dify

echo "[1/9] Delete Dify Ingress"
kubectl delete ingress -n "${NS_DIFY}" --all --ignore-not-found=true 2>/dev/null || true

echo "[2/9] Uninstall Dify (Helm)"
helm uninstall dify -n "${NS_DIFY}" 2>/dev/null || true

echo "[3/9] Delete Dify namespace"
kubectl delete namespace "${NS_DIFY}" --ignore-not-found=true --timeout=120s 2>/dev/null || true

echo "[4/9] Delete RAG Ingress"
if [[ -f rag-ingress.yaml ]]; then
  sed -e "s/k8s_project/${k8s_project}/g" -e "s/k8s_domain/${k8s_domain}/g" rag-ingress.yaml > rag-ingress.yaml_bak
  kubectl delete -f rag-ingress.yaml_bak -n "${NS}" --ignore-not-found=true 2>/dev/null || true
fi

echo "[5/9] Delete RAG CronJob / Job"
kubectl delete cronjob rag-ingestion-cronjob-cointutor rag-ingestion-cronjob-drillquiz -n "${NS}" --ignore-not-found=true 2>/dev/null || true
kubectl delete cronjob rag-ingestion -n "${NS}" --ignore-not-found=true 2>/dev/null || true
kubectl delete job rag-ingestion-job-cointutor rag-ingestion-job-drillquiz rag-ingestion-run qdrant-collection-init -n "${NS}" --ignore-not-found=true 2>/dev/null || true

echo "[6/9] Delete RAG Backend / Frontend"
kubectl delete -f cointutor/rag-backend.yaml -n "${NS}" --ignore-not-found=true 2>/dev/null || true
kubectl delete -f drillquiz/rag-backend-drillquiz.yaml -n "${NS}" --ignore-not-found=true 2>/dev/null || true
kubectl delete -f rag-frontend.yaml -n "${NS}" --ignore-not-found=true 2>/dev/null || true

echo "[7/9] Uninstall Qdrant (Helm)"
helm uninstall qdrant -n "${NS}" 2>/dev/null || true

echo "[8/9] Delete RAG namespace ${NS}"
kubectl delete namespace "${NS}" --ignore-not-found=true --timeout=120s 2>/dev/null || true

echo "[9/9] Cleanup wait"
sleep 5
kubectl get namespace "${NS_DIFY}" 2>/dev/null && echo "  → namespace ${NS_DIFY} still exists" || echo "  → namespace ${NS_DIFY} deleted"
kubectl get namespace "${NS}" 2>/dev/null && echo "  → namespace ${NS} still exists (check PVC etc. and delete manually)" || echo "  → namespace ${NS} deleted"

echo ""
echo "=== RAG + Dify stack uninstall complete ==="
echo "  Reinstall: ./install.sh"
