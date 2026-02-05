# RAG separation by topic (CoinTutor / DrillQuiz)

How to split documents in MinIO `rag-docs` by topic and fully separate using **unified collection names (option B)** + **separate Job/CronJob** + **two backends (approach A)**.

---

## 1. Separation strategy summary

| Item | CoinTutor | DrillQuiz |
|------|-----------|-----------|
| **MinIO path** | `rag-docs/raw/cointutor/` | `rag-docs/raw/drillquiz/` |
| **Qdrant collection** | `rag_docs_cointutor` | `rag_docs_drillquiz` |
| **Indexing Job** | `rag-ingestion-job-cointutor` | `rag-ingestion-job-drillquiz` |
| **Indexing CronJob** | `rag-ingestion-cronjob-cointutor` | `rag-ingestion-cronjob-drillquiz` |
| **RAG Backend** | `rag-backend` (COLLECTION=rag_docs_cointutor) | `rag-backend-drillquiz` (COLLECTION=rag_docs_drillquiz) |
| **Dify tool URL** | `http://rag-backend.rag.svc.cluster.local:8000/query` | `http://rag-backend-drillquiz.rag.svc.cluster.local:8000/query` |

- **Collections**: Do not use existing `rag_docs`; use only `rag_docs_cointutor` / `rag_docs_drillquiz` (option B).
- **Job/CronJob**: Separate YAML per topic.
- **Backends**: Approach A — two backend deployments for full separation.

---

## 2. MinIO folder structure

```
rag-docs/
  raw/
    cointutor/
      USE_CASES.md
      USER_GUIDE.md
    drillquiz/
      FAQ.md
      GUIDE.md
```

- **CoinTutor source docs**: In `tz-local/resource/rag/cointutor/` — `USE_CASES.md`, `USER_GUIDE.md`, `CoinTutor.yml` (Dify app template). Upload `.md` to MinIO `rag-docs/raw/cointutor/` then index.
- DrillQuiz docs: Upload only under `raw/drillquiz/`.

---

## 3. Qdrant collections (option B: unified names)

One collection per topic; vector size 1536, Cosine.

- **rag_docs_cointutor**: CoinTutor only.
- **rag_docs_drillquiz**: DrillQuiz only.
- Do not use existing `rag_docs`. If needed, re-index into `rag_docs_cointutor` then delete `rag_docs`.

`qdrant-collection-init.yaml` (or install.sh) is set up to create these two collections.

---

## 4. Indexing Job / CronJob separation

Same `ingest.py` and ConfigMap; only **environment variables** differ per topic.

### 4.1 CoinTutor

| Resource | MINIO_PREFIX | QDRANT_COLLECTION |
|----------|--------------|-------------------|
| Job | `raw/cointutor/` | `rag_docs_cointutor` |
| CronJob | `raw/cointutor/` | `rag_docs_cointutor` |

- **Job**: `kubectl apply -f rag-ingestion-job-cointutor.yaml`
- **One-off run**: `kubectl create job -n rag ingest-cointutor-1 --from=cronjob/rag-ingestion-cronjob-cointutor`

### 4.2 DrillQuiz

| Resource | MINIO_PREFIX | QDRANT_COLLECTION |
|----------|--------------|-------------------|
| Job | `raw/drillquiz/` | `rag_docs_drillquiz` |
| CronJob | `raw/drillquiz/` | `rag_docs_drillquiz` |

- **Job**: `kubectl apply -f rag-ingestion-job-drillquiz.yaml`
- **One-off run**: `kubectl create job -n rag ingest-drillquiz-1 --from=cronjob/rag-ingestion-cronjob-drillquiz`

---

## 5. Approach A: two backends (full separation)

Separate **Deployment + Service** per topic so separation is by URL.

### 5.1 CoinTutor backend

| Item | Description |
|------|--------------|
| **Deployment** | `rag-backend` (existing) |
| **Service** | `rag-backend` (port 8000) |
| **Env** | `QDRANT_COLLECTION=rag_docs_cointutor` |
| **URL (in-cluster)** | `http://rag-backend.rag.svc.cluster.local:8000` |

- Dify CoinTutor RAG tool: above URL + `POST /query` (body: `question`, `top_k` is enough).

### 5.2 DrillQuiz backend

| Item | Description |
|------|--------------|
| **Deployment** | `rag-backend-drillquiz` |
| **Service** | `rag-backend-drillquiz` (port 8000) |
| **Env** | `QDRANT_COLLECTION=rag_docs_drillquiz` |
| **URL (in-cluster)** | `http://rag-backend-drillquiz.rag.svc.cluster.local:8000` |

- Dify DrillQuiz RAG tool: above URL + `POST /query` (body: `question`, `top_k`).

### 5.3 Common

- CoinTutor backend uses ConfigMap `rag-backend-script`, DrillQuiz uses `rag-backend-drillquiz-script` (per topic). Scripts read `COLLECTION` env and query only that collection.
- Secrets: CoinTutor `rag-ingestion-secret-cointutor`, DrillQuiz `rag-ingestion-secret-drillquiz` (per topic; contents can be the same).

### 5.4 Dify connection

- **CoinTutor chatbot** → custom tool **CoinTutor RAG** → `http://rag-backend.rag.svc.cluster.local:8000/query`
- **DrillQuiz chatbot** → custom tool **DrillQuiz RAG** → `http://rag-backend-drillquiz.rag.svc.cluster.local:8000/query`

Different backend URLs keep traffic and deployment fully separate.

---

## 6. Approach B (reference): single backend + request parameter

Use one backend and pass collection via a `collection` parameter on `/query`.  
Consider only if you want simpler operations.

- `POST /query` body: `{ "question": "...", "top_k": 5, "collection": "rag_docs_drillquiz" }`
- In Dify, set different `collection` values per tool.

This repo is organized around **approach A (two backends)** for Job, CronJob, and docs.

---

## 7. Dify DrillQuiz chatbot

1. **Custom tool**: In OpenAPI schema set **server URL** to `http://rag-backend-drillquiz.rag.svc.cluster.local:8000`; keep the rest like CoinTutor RAG and register **DrillQuiz RAG**.
2. **App**: Create a new chat flow (e.g. DrillQuiz).
3. **Workflow**: Start → (optional) question classification → **tool (DrillQuiz RAG)** → LLM → Answer. `question` = `sys.query`.

---

## 8. RAG collection reset

Use `tz-local/resource/rag/reset-rag-collections.sh` to clear vector data and re-index.

```bash
cd tz-local/resource/rag
./reset-rag-collections.sh [cointutor|drillquiz|all] [reindex]
```

| Argument | Description |
|----------|-------------|
| `all` (default) | Delete and recreate both rag_docs_cointutor and rag_docs_drillquiz |
| `cointutor` | Reset only rag_docs_cointutor |
| `drillquiz` | Reset only rag_docs_drillquiz |
| `reindex` (second arg) | After reset, run indexing Job once for that topic |

Example: `./reset-rag-collections.sh cointutor reindex` — reset CoinTutor collection then run indexing Job.

**Why RAG still shows results after deleting files in MinIO**: The indexer (ingest.py) used to only **upsert** and did not delete from Qdrant, so re-running the Job after removing files in MinIO left **existing vectors**. The current ingest.py **drops and recreates the collection** on run, then upserts only files present in MinIO. After deleting files in MinIO and re-running the Job, the collection is cleared and only current MinIO objects are reflected.

---

## 9. Checklist

- [ ] Upload docs to MinIO `rag-docs/raw/cointutor/`, `raw/drillquiz/`
- [ ] Create Qdrant collections `rag_docs_cointutor`, `rag_docs_drillquiz` (install or manual)
- [ ] Apply CoinTutor Job/CronJob and run indexing once
- [ ] Apply DrillQuiz Job/CronJob and run indexing once
- [ ] Deploy RAG Backend (rag-backend) and RAG Backend DrillQuiz (rag-backend-drillquiz)
- [ ] In Dify: register CoinTutor RAG tool (rag-backend URL) and DrillQuiz RAG tool (rag-backend-drillquiz URL), then attach to each chatbot
- [ ] When reset is needed: use `tz-local/resource/rag/reset-rag-collections.sh`
