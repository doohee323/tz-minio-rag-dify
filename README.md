# tz-minio-rag-dify

This repository sets up a **RAG (Retrieval-Augmented Generation)** and **Dify chatbot** demo environment on Kubernetes. It installs, in order: Ingress NGINX, MinIO, Qdrant, topic-specific RAG backends (CoinTutor / DrillQuiz), and Dify.

## Usage

**Prerequisite**: A Kubernetes cluster and `kubectl` (or `KUBECONFIG`) must be available.

```bash
# Set KUBECONFIG if needed
export KUBECONFIG=~/.kube/your-config

# Install everything (existing components are skipped)
./bootstrap.sh
```

Install order: **Ingress NGINX** → **MinIO** → **RAG stack** → **Dify**.  
After install, create `rag-ingestion-secret-cointutor` and `rag-ingestion-secret-drillquiz` (MinIO, Gemini, etc.) for the RAG Backend to start. See `rag/README.md` and `docs/rag-multi-topic.md` for steps and checklists.

## Documentation

- `docs/rag-multi-topic.md` — Topic-based RAG separation (CoinTutor/DrillQuiz), MinIO paths, Dify tool URLs
- `docs/rag-requirements-and-plan.md` — Requirements and phase-by-phase execution plan
- `docs/additional-requirements.md` — Scale, control, traffic, iframe auth, tracking, F/U, and other operational considerations
- `docs/dify-drillquiz-embed-and-tracking.md` — DrillQuiz + Dify chat: user identity, tracking, F/U (embed / API proxy)
