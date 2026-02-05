# RAG stack + Dify (install.sh based)

Running `install.sh` once sets up the full stack: **RAG** (Qdrant, backend, frontend, indexer) and **Dify**. Re-running after uninstall produces the same setup.

## Install

```bash
cd tz-local/resource/rag
bash install.sh
```

- From inside VM: `/vagrant/tz-local/resource/rag/install.sh`
- From local: `KUBECONFIG=~/.kube/topzone.iptime.org.config bash install.sh`

### Required after install: Create Secrets (per topic)

RAG backends and indexer Job/CronJob use per-topic Secrets. Without `rag-ingestion-secret-cointutor` and `rag-ingestion-secret-drillquiz`, Backend Pods do not start and search returns `API key not valid`. **Run the following right after install** (both Secrets can use the same values).

```bash
MINIO_USER=$(kubectl get secret minio -n devops -o jsonpath='{.data.rootUser}' | base64 -d)
MINIO_PASS=$(kubectl get secret minio -n devops -o jsonpath='{.data.rootPassword}' | base64 -d)
GEMINI_KEY='your_valid_Gemini_API_key_here'

kubectl create secret generic rag-ingestion-secret-cointutor -n rag \
  --from-literal=MINIO_ACCESS_KEY="$MINIO_USER" \
  --from-literal=MINIO_SECRET_KEY="$MINIO_PASS" \
  --from-literal=GEMINI_API_KEY="$GEMINI_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic rag-ingestion-secret-drillquiz -n rag \
  --from-literal=MINIO_ACCESS_KEY="$MINIO_USER" \
  --from-literal=MINIO_SECRET_KEY="$MINIO_PASS" \
  --from-literal=GEMINI_API_KEY="$GEMINI_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
```

- Get `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey). **Replace** `'your_valid_Gemini_API_key_here'` with a real key.
- If you change the Secret **after** Pods are already running, restart the Backends for the new key to apply:
  ```bash
  kubectl rollout restart deployment/rag-backend deployment/rag-backend-drillquiz -n rag
  ```

## Uninstall (remove all resources)

```bash
cd tz-local/resource/rag
./uninstall.sh
```

- **Dify**: Removes Ingress → Helm → namespace `dify` (resets user and app data).
- **RAG**: Removes Ingress → CronJob/Job → Backend/Frontend → Qdrant(Helm) → namespace `rag`.
- Reinstall: `./install.sh`

## Components

**Per-topic folders**: CoinTutor / DrillQuiz separation (see docs/rag-multi-topic.md)

| Path | Description |
|------|-------------|
| `cointutor/rag-backend.yaml` | CoinTutor backend (rag_docs_cointutor) |
| `cointutor/rag-ingestion-job-cointutor.yaml` | CoinTutor indexing Job (raw/cointutor/ → rag_docs_cointutor) |
| `cointutor/rag-ingestion-cronjob-cointutor.yaml` | CoinTutor CronJob (daily 02:00) |
| `drillquiz/rag-backend-drillquiz.yaml` | DrillQuiz backend (rag_docs_drillquiz) |
| `drillquiz/rag-ingestion-job-drillquiz.yaml` | DrillQuiz indexing Job (raw/drillquiz/ → rag_docs_drillquiz) |
| `drillquiz/rag-ingestion-cronjob-drillquiz.yaml` | DrillQuiz CronJob (daily 02:30) |
| `namespace.yaml` | namespace `rag` |
| `qdrant-values.yaml` | Qdrant Helm values (single node, PVC) |
| `qdrant-collection-init.yaml` | Job: create collections rag_docs_cointutor, rag_docs_drillquiz |
| `rag-frontend.yaml` | Frontend (nginx + static UI, topic combo) |
| `rag-ingress.yaml` | Ingress (rag.*, rag-ui.*) — install.sh substitutes k8s_project/k8s_domain |
| `rag-ingestion-cronjob.yaml` | (Legacy) CronJob raw/ → rag_docs |
| `rag-ingestion-job.yaml` | (Legacy) one-off Job |
| `rag-ingestion-secret.example.yaml` | Secret example (MinIO + OpenAI/Gemini key per cointutor/drillquiz) |
| `reset-rag-collections.sh` | Reset Qdrant collections (cointutor \| drillquiz \| all) [reindex] |
| `scripts/ingest.py` | Indexer script (install.sh uploads as ConfigMap) |

## Indexer: MinIO raw/ → chunking → embedding → Qdrant rag_docs

**Flow**: PDF/txt under MinIO bucket `rag-docs` `raw/` → text extraction → chunking (500 chars, 50 overlap) → **embedding (OpenAI or Gemini)** → upsert into Qdrant collection `rag_docs`.

### 1. Create Secrets (required, per topic)

Indexer Job/CronJob and backends use per-topic Secrets. CoinTutor → `rag-ingestion-secret-cointutor`, DrillQuiz → `rag-ingestion-secret-drillquiz`. You only need **OpenAI** or **Gemini** (usually create both Secrets with the same values).

**Using Gemini (recommended):**
```bash
MINIO_USER=$(kubectl get secret minio -n devops -o jsonpath='{.data.rootUser}' | base64 -d)
MINIO_PASS=$(kubectl get secret minio -n devops -o jsonpath='{.data.rootPassword}' | base64 -d)
kubectl create secret generic rag-ingestion-secret-cointutor -n rag \
  --from-literal=MINIO_ACCESS_KEY="$MINIO_USER" --from-literal=MINIO_SECRET_KEY="$MINIO_PASS" \
  --from-literal=GEMINI_API_KEY='...'
kubectl create secret generic rag-ingestion-secret-drillquiz -n rag \
  --from-literal=MINIO_ACCESS_KEY="$MINIO_USER" --from-literal=MINIO_SECRET_KEY="$MINIO_PASS" \
  --from-literal=GEMINI_API_KEY='...'
```

**Using OpenAI:** Create both Secrets the same way and set `OPENAI_API_KEY`.

#### Copy MinIO secret (devops → rag)

When you already have a Secret and only need to add OpenAI/Gemini keys, copy MinIO keys from the **MinIO secret in the devops namespace**.

```bash
MINIO_USER=$(kubectl get secret minio -n devops -o jsonpath='{.data.rootUser}' | base64 -d)
MINIO_PASS=$(kubectl get secret minio -n devops -o jsonpath='{.data.rootPassword}' | base64 -d)
kubectl patch secret rag-ingestion-secret-cointutor -n rag -p '{"data":{"MINIO_ACCESS_KEY":"'$(echo -n "$MINIO_USER" | base64 | tr -d '\n')'","MINIO_SECRET_KEY":"'$(echo -n "$MINIO_PASS" | base64 | tr -d '\n')'"}}'
kubectl patch secret rag-ingestion-secret-drillquiz -n rag -p '{"data":{"MINIO_ACCESS_KEY":"'$(echo -n "$MINIO_USER" | base64 | tr -d '\n')'","MINIO_SECRET_KEY":"'$(echo -n "$MINIO_PASS" | base64 | tr -d '\n')'"}}'
```

### 2. MinIO bucket and raw/ upload

If bucket `rag-docs` does not exist when the indexer runs, it is **created automatically**. No need to create it manually.

- **To create in console**: MinIO web console → Buckets → Create Bucket → name `rag-docs`.
- **Upload documents**: Use prefix `raw/cointutor/` (or `raw/drillquiz/`) and upload **PDF, .txt, .md** under it. CoinTutor source docs are in `tz-local/resource/rag/cointutor/` (USE_CASES.md, USER_GUIDE.md); upload to MinIO `rag-docs/raw/cointutor/` to include them in CoinTutor indexing.

#### Indexer log messages

| Log message | Meaning | Action |
|-------------|---------|--------|
| `No objects under rag-docs/raw/. Upload PDF/txt to raw/ then re-run.` | Bucket/raw/ exists but **no files** | Upload PDF or .txt to `rag-docs` → `raw/` in MinIO console, then re-run Job/CronJob |
| `Embedding: OpenAI text-embedding-3-small` / `Embedding: Gemini ...` | Embedding provider/model in use | Informational, no action |
| `Created bucket rag-docs.` | Bucket was missing and **created automatically** | From next run, just add files under raw/ |
| `WARNING: Running pip as the 'root' user'` / `[notice] pip ...` | Warning from pip install inside container | Can be ignored |
| `  <filepath>: N chunks` / `Upserted ... points` | Chunking and Qdrant upsert done for that file | Normal |
| `Done. rag_docs points_count=<N>` | Indexing complete, N points in Qdrant | Normal |

### 3. One-off indexing (Job)

```bash
# CoinTutor
kubectl delete job rag-ingestion-job-cointutor -n rag --ignore-not-found
kubectl apply -f cointutor/rag-ingestion-job-cointutor.yaml -n rag
kubectl logs -n rag job/rag-ingestion-job-cointutor -f

# DrillQuiz
kubectl apply -f drillquiz/rag-ingestion-job-drillquiz.yaml -n rag
```

### 4. Scheduled run (CronJob)

CronJob `rag-ingestion` runs the same indexer script daily at 02:00. It works as-is if Secrets exist.

### 5. Payload (Qdrant)

Per-chunk payload: `doc_id`, `source`, `path`, `chunk_index`, `text`, `created_at` — used for RAG source and filtering.

### 6. How ingest.py runs inside K8s

| Step | Description |
|------|-------------|
| 1. ConfigMap | `install.sh` reads `scripts/ingest.py` and creates ConfigMap `rag-ingestion-script`. Key is filename `ingest.py`. |
| 2. Pod volume | CronJob/Job `volumes[]` uses `configMap: name: rag-ingestion-script`; container mounts with `volumeMounts: mountPath: /config`. |
| 3. Path in container | Script appears as **`/config/ingest.py`** inside the Pod. |
| 4. Run | Container `command`: `pip install ... && python /config/ingest.py`. I.e. start from Python image then run the mounted script. |
| 5. Env | `envFrom: secretRef: rag-ingestion-secret-cointutor` or `-drillquiz` injects MinIO/OpenAI/Gemini keys; QDRANT_HOST, MINIO_ENDPOINT etc. come from CronJob/Job `env[]`. |

- **CronJob**: At 02:00 daily the scheduler creates a Job → Pod starts → runs `ingest.py` as above.
- **One-off run**: `kubectl apply -f cointutor/rag-ingestion-job-cointutor.yaml -n rag` (or drillquiz) or `./reset-rag-collections.sh cointutor reindex`.

## Uninstall then reinstall

```bash
kubectl delete namespace rag
bash install.sh
```

## Configuration

- `k8s_project`, `k8s_domain`: From `/root/.k8s/project` or env. Defaults: `rag`, `local`.
- Qdrant single node: In `qdrant-values.yaml` set `config.cluster.enabled: false`.
- Schedule on specific nodes: Add `nodeSelector` or `affinity` in `qdrant-values.yaml`.
