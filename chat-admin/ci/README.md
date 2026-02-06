# TZ-Chat Gateway CI/CD

This folder contains the CI/CD setup for the **chat-admin** service: Jenkins pipeline, Kubernetes deployment script, and environment-specific manifests.

## Contents

| File | Purpose |
|------|--------|
| `Jenkinsfile` | Jenkins pipeline: credentials → checkout → build/push image → deploy |
| `k8s.sh` | Deployment script; applies manifests and (optionally) syncs ArgoCD |
| `k8s.yaml` | Base Kubernetes manifests |
| `k8s-dev.yaml` | Overrides for development |
| `k8s-qa.yaml` | Overrides for QA |
| `ci.sh` | Local script to simulate pipeline stages (build/deploy) |

## Pipeline (Jenkinsfile)

1. **Load Credentials** – Loads required secrets (see [Required credentials](#required-credentials)).
2. **Checkout** – Checkout source from Git.
3. **Build & Push Image** – Builds Docker image from `./chat-admin` and pushes to `REGISTRY/chat-admin:BUILD_NUMBER` (e.g. Docker Hub).
4. **Deploy to Kubernetes** – Runs `chat-admin/ci/k8s.sh` with `BUILD_NUMBER`, `GIT_BRANCH`, `NAMESPACE`, and action `deploy`.

### Branch → namespace

- **main** or **qa** → namespace `devops`
- Other branches → namespace `devops-dev`

ArgoCD sync is enabled only for the **qa** branch (`ARGOCD_ENABLED=true`).

## Deployment script (k8s.sh)

Run from repo root or from `chat-admin/`:

```bash
./ci/k8s.sh <BUILD_NUMBER> <GIT_BRANCH> <NAMESPACE> <ACTION> [ENV_FILE]
```

- **BUILD_NUMBER**: Image tag (e.g. Jenkins `BUILD_NUMBER`).
- **GIT_BRANCH**: Branch name (used for namespace/env selection).
- **NAMESPACE**: Kubernetes namespace (e.g. `devops`, `devops-dev`).
- **ACTION**: Usually `deploy`.
- **ENV_FILE**: Optional file to source for extra environment variables.

The script uses `k8s.yaml` and, when applicable, `k8s-dev.yaml` or `k8s-qa.yaml` to deploy the chat-admin app (and related resources) into the cluster. When ArgoCD is enabled, it can update the ArgoCD repo and sync the application.

## Required credentials (Jenkins)

Configure these in Jenkins (Credential IDs used by the pipeline):

| Credential ID | Usage |
|---------------|--------|
| `kubeconfig-jenkins` | File credential: kubeconfig for cluster access. Used during deploy and also created as Secret `chat-admin-kubeconfig-*` for the Pod (RAG trigger-reindex API uses kubectl). |
| `DOCKER_PASSWORD` | Docker registry (e.g. Docker Hub) push |
| `GITHUB_TOKEN` | Git operations |
| `CHAT_GATEWAY_JWT_SECRET` | Chat gateway JWT signing |
| `CHAT_GATEWAY_API_KEY` | Chat gateway API key |
| `POSTGRES_PASSWORD` | PostgreSQL password (K8s uses PostgreSQL; same as drillquiz devops DB) |
| `DIFY_API_KEY` | Dify API (fallback) |
| `DIFY_DRILLQUIZ_API_KEY` | Dify DrillQuiz app |
| `DIFY_COINTUTOR_API_KEY` | Dify CoinTutor app |
| `ARGOCD_PASSWORD` | ArgoCD (when `ARGOCD_ENABLED=true`) |

Optional: `BASE_DOMAIN` / `DOMAIN_PLACEHOLDER` (default `drillquiz.com`) for ingress/host names.

## Local testing (ci.sh)

Use `ci.sh` to run pipeline-like steps on your machine (build image, run k8s.sh) without Jenkins.

```bash
# From chat-admin directory
./ci/ci.sh

# Help and env dump
./ci/ci.sh --help
./ci/ci.sh --env
```

Set environment variables as needed (e.g. `BUILD_NUMBER`, `GIT_BRANCH`, `NAMESPACE`, `KUBECONFIG`, `CHAT_GATEWAY_JWT_SECRET`, Dify keys, ArgoCD vars). For deploy to work, `kubectl` must be configured (e.g. `KUBECONFIG`) and credentials available.

## Troubleshooting

- **Deploy fails in Jenkins**  
  Ensure `kubeconfig-jenkins` exists and the cluster is reachable. Check that `chat-admin/ci/k8s.sh` is present and executable in the workspace.

- **Image push fails**  
  Check `DOCKER_PASSWORD` (and registry URL) and that the job runs in a context where `docker build`/`docker push` are allowed.

- **Local ci.sh**  
  Run `chmod +x ci/ci.sh ci/k8s.sh` if needed. For deploy, set `KUBECONFIG` and any required env vars (JWT, Dify, ArgoCD) before running.
