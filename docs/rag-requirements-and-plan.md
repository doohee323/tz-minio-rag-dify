# RAG + Chatbot Requirements and Execution Plan

## 1. Requirements summary

### 1.1 Environment summary

| Item | Description |
|------|-------------|
| **Hyper-V host** | DESKTOP-KMDVQ1L |
| **VMs** | 3× Ubuntu 22.04 (ubuntu-22.04_0, _1, _2) |
| **VM RAM** | _0: ~4.1GB, _1: ~5.6GB, _2: ~6.7GB |
| **K8s access** | `KUBECONFIG=/Users/dhong/.kube/topzone.iptime.org.config` |
| **SSH (topzone.iptime.org)** | 12020, 12021(doohee323), 12023(eks-main-t) |

### 1.2 Existing infrastructure

- K8s cluster
- Ingress + TLS
- MinIO (namespace: `devops`, Helm minio/minio 5.4.0, console exposed via Ingress)

### 1.3 To be built

- **RAG stack**: Qdrant, RAG backend, RAG frontend, Ingestion/Job
- **Chatbot**: Dify (easiest install + RAG support + Web UI, MinIO/Qdrant integration)
- **RAG operations in 6 steps**: MinIO bucket rules → Qdrant collections → indexing → metadata rules → search test → CronJob auto-indexing

### 1.4 Resource guide (per Pod)

| Component | Approx. RAM |
|-----------|-------------|
| RAG backend | 1–2GB |
| RAG frontend | 0.5GB |
| Qdrant | 2–4GB |
| Ingestion/Job (when running) | 1–2GB |
| Buffer | 2GB |

**Scenario A (recommended)**: Run RAG on a single VM (e.g. ubuntu-22.04_2, ~6.7GB)  
- MinIO access + Qdrant + RAG backend/frontend + Dify  
- Benefits: simple, keep network layout, works with current state  

**What “use a specific VM” means**: Give the scheduler a **hint** so workloads run on that node.  
- Use **nodeSelector**, **nodeAffinity**, or **nodeName** so RAG Pods (Qdrant, RAG backend/frontend, Ingestion Job, etc.) run only on that node.  
- Example: if the node has a label like `node.kubernetes.io/hostname=ubuntu-22-04-2`, set that in Deployment/Job via `nodeSelector` or `affinity`.  
- Without a hint the scheduler can place Pods on any node; to enforce “only this VM”, you must set scheduling explicitly.

### 1.5 Is this a typical setup? (validation summary)

**Conclusion: Yes, this is a typical (standard) RAG setup.**

| Component | Typical? | Notes |
|-----------|----------|-------|
| **Document store (MinIO/S3)** | ✅ Yes | “Object store + vector DB” is standard for production RAG. MinIO is S3-compatible and commonly referenced in LangChain/official docs. |
| **Bucket layout (raw/processed/chunks)** | ✅ Yes | Separating raw, processed, and chunks is common in data lakes and RAG pipelines. |
| **Vector DB (Qdrant)** | ✅ Yes | Qdrant, Weaviate, Pinecone, pgvector are widely used for RAG. Qdrant is often chosen for open-source, self-hosted, performance. Dify Enterprise recommends Qdrant as vector DB. |
| **Indexing (batch/CronJob)** | ✅ Yes | “Documents → chunks → embedding → vector DB” is done as batch (scheduled) or event (webhook on upload). CronJob batch is simple and common for initial/small scale. |
| **Metadata (doc_id, source, path, page)** | ✅ Yes | Putting source, page, path in chunk payload for citation/filtering is commonly recommended in RAG quality guides. |
| **Dify + RAG** | ✅ Yes | Dify is an open-source platform with RAG, chatbot, Web UI; MinIO/vector DB (e.g. Qdrant) integration appears often in docs and examples. |
| **K8s deployment** | ✅ Yes | Deploying RAG services on Kubernetes is used in cloud and on-prem; good for scaling and operations. |

**Alternatives**  
- **Indexing trigger**: Current plan is “CronJob on a schedule”. For more real-time, MinIO bucket notification → webhook → indexer is also common.  
- **Vector DB**: pgvector is often used below ~5M vectors; Qdrant is a typical choice.  
- **Advanced search**: Production often adds BM25+embedding hybrid and reranking; at this stage “embedding + Qdrant” alone is a typical first-step setup.

---

## 2. Execution plan (by Phase)

### Phase 0: Pre-checks

| # | Task | Command / check |
|---|------|------------------|
| 0-1 | Verify K8s access | `KUBECONFIG=/Users/dhong/.kube/topzone.iptime.org.config kubectl get nodes` |
| 0-2 | Verify MinIO/Ingress namespace and services | `kubectl -n devops get svc,pods` |
| 0-3 | Decide RAG namespace | e.g. `rag` (create if new) |

---

### Phase 1: MinIO bucket/path rules for RAG

| # | Task | Description |
|---|------|--------------|
| 1-1 | Create bucket (if missing) | Bucket name: `rag-docs` |
| 1-2 | Define prefix rules | `raw/` (source), `processed/` (preprocessed), `chunks/` (chunks/metadata), `indexes/` (optional) |
| 1-3 | Apply via MinIO console or mc/API | If bucket exists, just document the rules |

**Outcome**: MinIO `rag-docs` bucket + documented prefix rules

---

### Phase 2: Deploy Qdrant and create collection

| # | Task | Description |
|---|------|--------------|
| 2-1 | Deploy Qdrant | Deployment/Service (or Helm) in `rag` namespace, 2–4GB resources |
| 2-2 | Expose Ingress/Service | Internal 6333; expose 6333 via Ingress if needed |
| 2-3 | Choose embedding dimension | OpenAI text-embedding-3-small → 1536 (default recommendation) |
| 2-4 | Create collection | `rag_docs`, vectors size=1536, distance=Cosine |
| 2-5 | Verify | `GET /collections`, `GET /collections/rag_docs` |

**Example (after port-forward)**  
```bash
kubectl -n rag port-forward svc/qdrant 6333:6333
# In another terminal
curl -X PUT "http://localhost:6333/collections/rag_docs" \
  -H "Content-Type: application/json" \
  -d '{"vectors": { "size": 1536, "distance": "Cosine" }}'
curl "http://localhost:6333/collections"
```

---

### Phase 3: Deploy RAG Backend / Frontend

| # | Task | Description |
|---|------|--------------|
| 3-1 | Deploy RAG backend | Configure MinIO/Qdrant URL and auth; expose `/query` or `/chat` etc. |
| 3-2 | Deploy RAG frontend | Connect to backend URL; question→answer UI |
| 3-3 | Ingress + TLS | Expose backend/frontend on a host (e.g. rag.example.com) |
| 3-4 | Check API docs | Verify endpoints and parameters at `/docs` or `/swagger` |

**Outcome**: RAG API working; queries possible from frontend

---

### Phase 4: Indexer (Ingestion) setup and first run

| # | Task | Description |
|---|------|--------------|
| 4-1 | Check indexer components | From `kubectl -n rag get pods` confirm extractor/ingest/worker etc. |
| 4-2 | Check indexer logs/docs | Confirm run method, MinIO path, Qdrant collection name |
| 4-3 | Upload test docs to MinIO `raw/` | e.g. 1–2 PDFs |
| 4-4 | Run indexing Job once | Documents → chunks → embedding → store in Qdrant `rag_docs` |
| 4-5 | Check Qdrant points_count | Success when `points_count` > 0 |

**Outcome**: Vector data loaded into Qdrant

---

### Phase 5: Metadata rules and search quality

| # | Task | Description |
|---|------|--------------|
| 5-1 | Define chunk payload rules | doc_id, source, path, page, section, created_at, updated_at, (optional) acl |
| 5-2 | Configure indexer to set payload | Update code/config; re-run indexing if needed |
| 5-3 | Search→generate test | Query via RAG API; verify source/page citation |
| 5-4 | Tune quality | Chunk size, overlap, top_k, etc. |

**Outcome**: Metadata rules documented; search results with citable sources

---

### Phase 6: Auto-indexing (CronJob)

| # | Task | Description |
|---|------|--------------|
| 6-1 | Create CronJob resource | Schedule e.g. daily 02:00; same indexer image/script |
| 6-2 | Scan MinIO `raw/` → index only new | Apply logic if available; otherwise start with full re-index |
| 6-3 | Deploy and monitor | `kubectl -n rag get cronjobs`; verify with a manual run and logs |

**Outcome**: Periodic auto-indexing in place

---

### Phase 7: Dify chatbot setup

| # | Task | Description |
|---|------|--------------|
| 7-1 | Choose Dify install method | **K8s Helm deploy** (`tz-local/resource/dify/install.sh`) |
| 7-2 | Use Helm chart | Community chart [BorisPolonsky/dify-helm](https://github.com/BorisPolonsky/dify-helm). Document repo clone as fallback if add fails |
| 7-3 | Configure | `values.yaml`: vector DB=Qdrant(`qdrant.rag.svc.cluster.local:6333`), file=MinIO (S3, devops NS), Ingress (Jenkins-style host) |
| 7-4 | Connect RAG and chatbot in Web UI | Data source (MinIO/local), vector DB, question→answer flow — see `tz-local/resource/dify/README.md` |

**Outcome**: RAG-backed chatbot working from Dify Web UI  
**Config location**: `tz-local/resource/dify/` (install.sh, values.yaml, dify-ingress.yaml, README.md)

---

## 3. Execution order summary

```
Phase 0: Pre-checks (K8s, MinIO, namespace)
    ↓
Phase 1: MinIO rag-docs bucket + prefix rules
    ↓
Phase 2: Deploy Qdrant + collection (rag_docs, dim=1536)
    ↓
Phase 3: Deploy RAG Backend/Frontend + Ingress
    ↓
Phase 4: Indexer setup and first run → load data into Qdrant
    ↓
Phase 5: Metadata rules + search/citation test
    ↓
Phase 6: CronJob auto-indexing
    ↓
Phase 7: Install Dify and connect RAG chatbot
```

---

## 4. K8s access commands (local Mac)

```bash
export KUBECONFIG=/Users/dhong/.kube/topzone.iptime.org.config
kubectl get nodes
kubectl -n devops get svc,pods
# When using RAG namespace
kubectl create namespace rag
kubectl -n rag get all
```

**Note**: If the server in `topzone.iptime.org.config` is `https://kubernetes.default.svc.cluster.local:26443`, you may need an SSH tunnel (e.g. `-L 26443:...`) to reach the API server. When running inside the VM, the same config can be used as-is.

---

## 5. Checklist (mark ✓ when done)

- [ ] Phase 0: K8s, MinIO, namespace verified
- [ ] Phase 1: `rag-docs` bucket + raw/processed/chunks rules
- [ ] Phase 2: Qdrant deployed, `rag_docs` collection (1536), verified
- [ ] Phase 3: RAG backend/frontend deployed, Ingress, API docs verified
- [ ] Phase 4: Indexer run once, Qdrant points_count > 0
- [ ] Phase 5: Metadata rules, search/citation test
- [ ] Phase 6: CronJob auto-indexing
- [ ] Phase 7: Dify installed and RAG chatbot connected (`tz-local/resource/dify/install.sh` + README)

---

## 6. Pause point / current state

**Resource readiness**: Manifests and scripts for Phase 2–7 are already in the repo.

| Location | Contents |
|----------|----------|
| `tz-local/resource/rag/` | namespace, Qdrant (Helm), collection init Job, RAG backend/frontend, Ingress, indexer Job/CronJob, `scripts/ingest.py` |
| `tz-local/resource/dify/` | install.sh (Helm), values.yaml, dify-ingress.yaml, minio-bucket-job, status.sh, README |

**Deployment not yet executed** — checklist items are unchecked. Resume from the phase that matches what is actually applied on the cluster.

**Resume order**

1. **Phase 0**  
   Verify K8s and MinIO with `KUBECONFIG=... kubectl get nodes` and `kubectl -n devops get svc,pods`; then `kubectl create namespace rag` if needed.

2. **Phase 1**  
   Create bucket `rag-docs` in MinIO console and document prefix rules (raw/processed/chunks).

3. **Phase 2–3**  
   Deploy RAG stack:  
   `cd tz-local/resource/rag && bash install.sh`  
   → Qdrant, collection `rag_docs`, RAG backend/frontend, Ingress applied.

4. **Phase 4**  
   Create `rag-ingestion-secret-cointutor`, `rag-ingestion-secret-drillquiz` (MinIO + OpenAI or Gemini keys),  
   upload test docs to MinIO `rag-docs` bucket `raw/` →  
   run indexing once (e.g. `kubectl -n rag create job --from=cronjob/rag-ingestion-cronjob ingest-manual-1`) →  
   verify Qdrant points_count.

5. **Phase 5–6**  
   After metadata and search tests, confirm CronJob schedule (`kubectl -n rag get cronjobs`).

6. **Phase 7**  
   (Optional) Verify NFS StorageClass `nfs-client`, then  
   `cd tz-local/resource/dify && bash install.sh`  
   → Access Dify Web UI and connect RAG and chatbot (see `tz-local/resource/dify/README.md`).

Mark the checklist items with `[x]` as you complete each phase to track progress.
