#!/usr/bin/env bash
# Dify chatbot install (Phase 7): Helm + RAG (Qdrant/rag, MinIO/devops), Ingress
# Prerequisites: RAG (Qdrant·rag_docs), NFS StorageClass (nfs-client, RWX), optional devops/MinIO

#set -e
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

shopt -s expand_aliases
KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"
alias k="kubectl --kubeconfig ${KUBECONFIG}"

k8s_project="${k8s_project:-$(prop 'project' 'project')}"
k8s_domain="${k8s_domain:-$(prop 'project' 'domain')}"
[[ -z "$k8s_project" ]] && k8s_project="default"
[[ -z "$k8s_domain" ]] && k8s_domain="drillquiz.com"

NS=dify

# Reinstall (e.g. storage change): ./install.sh reinstall → uninstall Helm + clean PVC/Secret then reinstall
if [[ "${1:-}" == "reinstall" ]]; then
  echo "[0/5] Uninstall Helm and clean PVC/Secret (reinstall)"
  helm uninstall dify -n "${NS}" 2>/dev/null || true
  k delete pvc -n "${NS}" dify dify-plugin-daemon 2>/dev/null || true
  k delete secret -n "${NS}" dify-postgresql dify-redis 2>/dev/null || true
  sleep 3
fi

echo "[1/5] Namespace ${NS}"
k create namespace "${NS}" 2>/dev/null || true

echo "[2/5] Helm repo (Dify community chart)"
if ! helm repo list 2>/dev/null | grep -q dify; then
  # Community chart: https://github.com/BorisPolonsky/dify-helm
  helm repo add dify https://borispolonsky.github.io/dify-helm 2>/dev/null || {
    echo "Repo add failed. Try: git clone https://github.com/BorisPolonsky/dify-helm && helm install dify ./dify-helm/charts/dify -n ${NS} -f values.yaml_bak"
    exit 1
  }
fi
helm repo update

echo "[3/5] Substitute values.yaml (k8s_project, k8s_domain, access URL)"
cp -f values.yaml values.yaml_bak
sed -i.bak "s/k8s_project/${k8s_project}/g" values.yaml_bak
sed -i.bak "s/k8s_domain/${k8s_domain}/g" values.yaml_bak
# Base URL for access. For port-forward: DIFY_BASE_URL=http://localhost:8080 bash install.sh
DIFY_BASE_URL_REPLACE="${DIFY_BASE_URL:-https://dify.${k8s_domain}}"
sed -i.bak "s|DIFY_BASE_URL_REPLACE|${DIFY_BASE_URL_REPLACE}|g" values.yaml_bak

echo "[3b/5] MinIO Secret (dify-minio-secret) — copy from devops/minio if not present"
if ! k get secret dify-minio-secret -n "${NS}" &>/dev/null; then
  if k get secret minio -n devops &>/dev/null; then
    MINIO_USER=$(k get secret minio -n devops -o jsonpath='{.data.rootUser}' | base64 -d 2>/dev/null)
    MINIO_PASS=$(k get secret minio -n devops -o jsonpath='{.data.rootPassword}' | base64 -d 2>/dev/null)
    if [[ -n "$MINIO_USER" && -n "$MINIO_PASS" ]]; then
      k create secret generic dify-minio-secret -n "${NS}" \
        --from-literal=S3_ACCESS_KEY="$MINIO_USER" \
        --from-literal=S3_SECRET_KEY="$MINIO_PASS"
      echo "  → dify-minio-secret created (from devops/minio)"
    else
      echo "  → Failed to read devops/minio Secret. Create manually: kubectl create secret generic dify-minio-secret -n ${NS} --from-literal=S3_ACCESS_KEY=... --from-literal=S3_SECRET_KEY=..."
    fi
  else
    echo "  → devops/minio not found. For MinIO, create manually: kubectl create secret generic dify-minio-secret -n ${NS} --from-literal=S3_ACCESS_KEY=... --from-literal=S3_SECRET_KEY=..."
  fi
fi

echo "[3c/5] Create MinIO bucket dify (when dify-minio-secret exists)"
if k get secret dify-minio-secret -n "${NS}" &>/dev/null && [[ -f minio-bucket-job.yaml ]]; then
  k delete job minio-create-bucket-dify -n "${NS}" --ignore-not-found=true 2>/dev/null
  k apply -f minio-bucket-job.yaml -n "${NS}" 2>/dev/null
  k wait --for=condition=complete job/minio-create-bucket-dify -n "${NS}" --timeout=60s 2>/dev/null || true
fi

echo "[4/5] Helm upgrade --install Dify"
helm upgrade --install dify dify/dify -n "${NS}" -f values.yaml_bak --wait --timeout 600s 2>/dev/null || \
  helm upgrade --install dify dify/dify -n "${NS}" -f values.yaml_bak

echo "[5/5] Apply Ingress separately"
if [[ -f dify-ingress.yaml ]]; then
  sed -e "s/k8s_project/${k8s_project}/g" -e "s/k8s_domain/${k8s_domain}/g" dify-ingress.yaml > dify-ingress.yaml_bak
  k apply -f dify-ingress.yaml_bak -n "${NS}" 2>/dev/null || true
fi

echo "[5b/5] HPA (default min=1, max=1)"
if [[ -f dify-hpa.yaml ]]; then
  k apply -f dify-hpa.yaml -n "${NS}" 2>/dev/null || true
fi

echo ""
echo "=== Dify install complete (Phase 7) ==="
echo "  Console:  https://dify.default.${k8s_project}.${k8s_domain} or https://dify.${k8s_domain}"
echo "  Vector DB:  Qdrant (rag namespace, rag_docs collection)"
echo "  Storage:   MinIO S3 (devops, bucket dify) — use when S3_ACCESS_KEY/S3_SECRET_KEY from Secret"
echo "  RAG:  Connect data source / knowledge base in Web UI then configure chatbot flow (see README)"
echo "  Monitor: ./status.sh (once) or ./status.sh watch (live)"
echo ""
k get pods,svc,pvc,ingress -n "${NS}" 2>/dev/null || true
exit 0
