#!/usr/bin/env bash
# RAG stack install: single run of install.sh sets up everything (re-runnable after uninstall)
# - Namespace rag, Qdrant (Helm), collections, RAG backend/frontend, Ingress, Ingestion CronJob
# - Dify is installed separately via bootstrap.sh install_dify

#set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# prop (harbor/minio pattern): read project, domain from /root/.k8s/project
if [[ -f /root/.bashrc ]]; then
  source /root/.bashrc
fi
function prop {
  key="${2}="
  file="/root/.k8s/${1}"
  if [[ ! -f "$file" ]]; then
    echo ""
    return
  fi
  rslt=$(grep "${3:-}" "$file" -A 10 | grep "$key" | head -n 1 | cut -d '=' -f2 | sed 's/ //g')
  [[ -z "$rslt" ]] && key="${2} = " && rslt=$(grep "${3:-}" "$file" -A 10 | grep "$key" | head -n 1 | cut -d '=' -f2 | sed 's/ //g')
  echo "$rslt" | tr -d '\n' | tr -d '\r'
}

shopt -s expand_aliases
KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"
alias k="kubectl --kubeconfig ${KUBECONFIG}"

k8s_project="${k8s_project:-$(prop 'project' 'project')}"
k8s_domain="${k8s_domain:-$(prop 'project' 'domain')}"
[[ -z "$k8s_project" ]] && k8s_project="rag"
[[ -z "$k8s_domain" ]] && k8s_domain="drillquiz.com"

NS=rag

echo "[1/7] Namespace ${NS}"
kubectl apply -f namespace.yaml

echo "[2/7] Qdrant (Helm)"
helm repo add qdrant https://qdrant.github.io/qdrant-helm 2>/dev/null || true
helm repo update
helm upgrade --install qdrant qdrant/qdrant -n "${NS}" -f qdrant-values.yaml --wait --timeout 120s 2>/dev/null || \
  helm upgrade --install qdrant qdrant/qdrant -n "${NS}" -f qdrant-values.yaml

echo "[3/7] Wait for Qdrant Pod"
kubectl wait --for=condition=ready pod -l "app.kubernetes.io/name=qdrant" -n "${NS}" --timeout=180s 2>/dev/null || \
  kubectl wait --for=condition=ready pod -l "app=qdrant" -n "${NS}" --timeout=180s 2>/dev/null || \
  sleep 30

echo "[4/7] Create Qdrant collections (rag_docs_cointutor, rag_docs_drillquiz)"
kubectl delete job qdrant-collection-init -n "${NS}" --ignore-not-found=true
kubectl apply -f qdrant-collection-init.yaml -n "${NS}"
kubectl wait --for=condition=complete job/qdrant-collection-init -n "${NS}" --timeout=120s 2>/dev/null || sleep 15

echo "[5/7] RAG Backend (CoinTutor + DrillQuiz) / Frontend"
kubectl apply -f cointutor/rag-backend.yaml -n "${NS}"
kubectl apply -f drillquiz/rag-backend-drillquiz.yaml -n "${NS}"
kubectl apply -f rag-frontend.yaml -n "${NS}"

echo "[5b/7] HPA (default min=1, max=1)"
kubectl apply -f rag-hpa.yaml -n "${NS}" 2>/dev/null || true

echo "[5c/7] ResourceQuota (rag namespace limits)"
kubectl apply -f rag-resource-quota.yaml -n "${NS}" 2>/dev/null || true

echo "[6/7] Ingress (rag, rag-ui)"
sed -e "s/k8s_project/${k8s_project}/g" -e "s/k8s_domain/${k8s_domain}/g" rag-ingress.yaml > rag-ingress.yaml_bak
kubectl apply -f rag-ingress.yaml_bak -n "${NS}"

echo "[7/7] Ingestion (ConfigMap + CronJob: cointutor, drillquiz)"
if [[ -f "${SCRIPT_DIR}/scripts/ingest.py" ]]; then
  kubectl create configmap rag-ingestion-script --from-file="${SCRIPT_DIR}/scripts/ingest.py" -n "${NS}" --dry-run=client -o yaml | kubectl apply -f -
fi
kubectl apply -f cointutor/rag-ingestion-cronjob-cointutor.yaml -n "${NS}"
kubectl apply -f drillquiz/rag-ingestion-cronjob-drillquiz.yaml -n "${NS}"

echo ""
echo "=== RAG stack install complete ==="
echo "  Namespace: ${NS}"
echo "  Backend:   rag.default.${k8s_project}.${k8s_domain}, rag.${k8s_domain}"
echo "  Frontend:  rag-ui.default.${k8s_project}.${k8s_domain}, rag-ui.${k8s_domain}"
echo "  Qdrant:    kubectl -n ${NS} port-forward svc/qdrant 6333:6333"
echo "  MinIO:     devops namespace (create rag-docs bucket via console)"
echo "  Indexer:   Create Secret rag-ingestion-secret-cointutor, rag-ingestion-secret-drillquiz then use Job/CronJob (see docs/rag-multi-topic.md)"
kubectl get pods,svc,ingress,cronjob -n "${NS}" 2>/dev/null || true
if ! kubectl get secret rag-ingestion-secret-cointutor -n "${NS}" &>/dev/null || ! kubectl get secret rag-ingestion-secret-drillquiz -n "${NS}" &>/dev/null; then
  echo ""
  echo "⚠️  Missing Secret rag-ingestion-secret-cointutor or rag-ingestion-secret-drillquiz; Backend Pods will be in CreateContainerConfigError."
  echo "   Create both as below, then Pods will start (see README.md)."
  echo "   MINIO_USER=\$(kubectl get secret minio -n devops -o jsonpath='{.data.rootUser}' | base64 -d)"
  echo "   MINIO_PASS=\$(kubectl get secret minio -n devops -o jsonpath='{.data.rootPassword}' | base64 -d)"
  echo "   kubectl create secret generic rag-ingestion-secret-cointutor -n ${NS} --from-literal=MINIO_ACCESS_KEY=\"\$MINIO_USER\" --from-literal=MINIO_SECRET_KEY=\"\$MINIO_PASS\" --from-literal=GEMINI_API_KEY='YOUR_GEMINI_KEY'"
  echo "   kubectl create secret generic rag-ingestion-secret-drillquiz -n ${NS} --from-literal=MINIO_ACCESS_KEY=\"\$MINIO_USER\" --from-literal=MINIO_SECRET_KEY=\"\$MINIO_PASS\" --from-literal=GEMINI_API_KEY='YOUR_GEMINI_KEY'"
fi
exit 0
