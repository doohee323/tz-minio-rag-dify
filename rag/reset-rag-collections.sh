#!/usr/bin/env bash
# RAG Qdrant collection reset: delete and recreate collections (clear vector data)
# Usage: ./reset-rag-collections.sh [cointutor|drillquiz|all] [reindex]
#   - No arg or all: reset rag_docs (legacy) + rag_docs_cointutor, rag_docs_drillquiz
#   - cointutor / drillquiz: reset that collection only
#   - reindex: run indexing Job once for the topic after reset (optional)
#
# Examples: ./reset-rag-collections.sh all
#           ./reset-rag-collections.sh cointutor reindex

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"
NS="${NS:-rag}"
TOPIC="${1:-all}"
REINDEX="${2:-}"

POD_NAME="rag-qdrant-reset-$$"

# Run curl from a Pod that can reach Qdrant (inside cluster)
run_reset() {
  local topic="$1"
  local cmd
  case "$topic" in
    cointutor)
      cmd='curl -s -X DELETE http://qdrant:6333/collections/rag_docs_cointutor || true; curl -s -X PUT http://qdrant:6333/collections/rag_docs_cointutor -H "Content-Type: application/json" -d "{\"vectors\":{\"size\":1536,\"distance\":\"Cosine\"}}"; echo cointutor ok'
      ;;
    drillquiz)
      cmd='curl -s -X DELETE http://qdrant:6333/collections/rag_docs_drillquiz || true; curl -s -X PUT http://qdrant:6333/collections/rag_docs_drillquiz -H "Content-Type: application/json" -d "{\"vectors\":{\"size\":1536,\"distance\":\"Cosine\"}}"; echo drillquiz ok'
      ;;
    all|*)
      # Delete legacy rag_docs (do not recreate). Recreate cointutor/drillquiz only
      cmd='curl -s -X DELETE http://qdrant:6333/collections/rag_docs || true; curl -s -X DELETE http://qdrant:6333/collections/rag_docs_cointutor || true; curl -s -X PUT http://qdrant:6333/collections/rag_docs_cointutor -H "Content-Type: application/json" -d "{\"vectors\":{\"size\":1536,\"distance\":\"Cosine\"}}"; curl -s -X DELETE http://qdrant:6333/collections/rag_docs_drillquiz || true; curl -s -X PUT http://qdrant:6333/collections/rag_docs_drillquiz -H "Content-Type: application/json" -d "{\"vectors\":{\"size\":1536,\"distance\":\"Cosine\"}}"; echo all ok'
      ;;
  esac

  kubectl --kubeconfig "${KUBECONFIG}" run "${POD_NAME}" -n "${NS}" \
    --restart=Never \
    --image=curlimages/curl \
    -- sh -c "$cmd"

  echo "Running Pod ${POD_NAME} (Qdrant access)..."
  for i in $(seq 1 30); do
    phase=$(kubectl --kubeconfig "${KUBECONFIG}" get pod "${POD_NAME}" -n "${NS}" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
    [[ "$phase" == "Succeeded" ]] && break
    [[ "$phase" == "Failed" ]] && break
    sleep 2
  done
  kubectl --kubeconfig "${KUBECONFIG}" logs "pod/${POD_NAME}" -n "${NS}" 2>/dev/null || true
  kubectl --kubeconfig "${KUBECONFIG}" delete pod "${POD_NAME}" -n "${NS}" --ignore-not-found=true --wait=false 2>/dev/null || true
}

echo "[1/2] Qdrant collection reset (topic=${TOPIC})"
run_reset "${TOPIC}"
echo "Reset complete."
echo "  → If RAG UI still shows old results, hard refresh (Ctrl+Shift+R)."

if [[ "${REINDEX}" == "reindex" ]]; then
  echo "[2/2] Run indexing Job once"
  case "$TOPIC" in
    cointutor)
      kubectl --kubeconfig "${KUBECONFIG}" delete job rag-ingestion-job-cointutor -n "${NS}" --ignore-not-found=true
      kubectl --kubeconfig "${KUBECONFIG}" apply -f "${SCRIPT_DIR}/cointutor/rag-ingestion-job-cointutor.yaml" -n "${NS}"
      echo "  → rag-ingestion-job-cointutor started. Check: kubectl get jobs -n ${NS}"
      ;;
    drillquiz)
      kubectl --kubeconfig "${KUBECONFIG}" delete job rag-ingestion-job-drillquiz -n "${NS}" --ignore-not-found=true
      kubectl --kubeconfig "${KUBECONFIG}" apply -f "${SCRIPT_DIR}/drillquiz/rag-ingestion-job-drillquiz.yaml" -n "${NS}"
      echo "  → rag-ingestion-job-drillquiz started. Check: kubectl get jobs -n ${NS}"
      ;;
    all|*)
      kubectl --kubeconfig "${KUBECONFIG}" delete job rag-ingestion-job-cointutor -n "${NS}" --ignore-not-found=true
      kubectl --kubeconfig "${KUBECONFIG}" delete job rag-ingestion-job-drillquiz -n "${NS}" --ignore-not-found=true
      kubectl --kubeconfig "${KUBECONFIG}" apply -f "${SCRIPT_DIR}/cointutor/rag-ingestion-job-cointutor.yaml" -n "${NS}"
      kubectl --kubeconfig "${KUBECONFIG}" apply -f "${SCRIPT_DIR}/drillquiz/rag-ingestion-job-drillquiz.yaml" -n "${NS}"
      echo "  → CoinTutor / DrillQuiz indexing Jobs started. Check: kubectl get jobs -n ${NS}"
      ;;
  esac
else
  echo "[2/2] Skipping reindex. To run: ./reset-rag-collections.sh ${TOPIC} reindex"
fi
echo "Done."
