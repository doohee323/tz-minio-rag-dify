#!/usr/bin/env bash
# Dify install status (dify namespace Pod/PVC/SVC/Ingress)
# Usage: ./status.sh [watch] — omit watch for one-shot; with watch, refresh every 2s

NS="${DIFY_NS:-dify}"
KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"
WATCH="${1:-}"

kubectl --kubeconfig "${KUBECONFIG}" get pods,svc,pvc,ingress -n "${NS}" 2>/dev/null || {
  echo "Namespace ${NS} not found or kubectl access failed. Check KUBECONFIG."
  exit 1
}

if [[ "$WATCH" == "watch" ]] || [[ "$WATCH" == "-w" ]]; then
  echo ""
  echo "--- Pod status live (Ctrl+C to stop) ---"
  kubectl --kubeconfig "${KUBECONFIG}" get pods -n "${NS}" -w
fi
