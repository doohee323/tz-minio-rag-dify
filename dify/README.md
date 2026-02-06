# Dify chatbot (Phase 7)

Install Dify chatbot integrated with the RAG stack (Qdrant, MinIO). One run of `install.sh` does Helm deploy and applies Ingress.

## Install (7-1, 7-2)

**Prerequisites**
- Qdrant deployed in RAG namespace and `rag_docs` collection created
- **NFS StorageClass** (`nfs-client`, ReadWriteMany): api/worker share the same PVC, so RWX is required.  
  If not installed: run `tz-chatbot/dynamic-provisioning/nfs/install.sh` (if available), then check `k get storageclass` for `nfs-client`.
- (Optional) MinIO deployed in devops namespace — for Dify file storage

```bash
cd tz-chatbot/dify
bash install.sh
```

- From inside VM: `/vagrant/tz-chatbot/dify/install.sh`
- From local: `KUBECONFIG=~/.kube/your.config bash install.sh`

**Install method**: K8s Helm deploy (Community chart [BorisPolonsky/dify-helm](https://github.com/BorisPolonsky/dify-helm)).  
If adding the Helm repo fails: `git clone https://github.com/BorisPolonsky/dify-helm` then `helm install dify ./dify-helm/charts/dify -n dify -f values.yaml_bak`

## Configuration (7-3)

| Item | Setting |
|------|---------|
| **PVC/Storage** | NFS `storageClass: nfs-client`, `accessModes: ReadWriteMany` (shared by api/worker/pluginDaemon) |
| **Vector DB** | Qdrant `http://qdrant.rag.svc.cluster.local:6333` (rag namespace, collection `rag_docs`) |
| **File storage** | MinIO S3 (devops, bucket `dify`). Secret `dify-minio-secret` must have `S3_ACCESS_KEY`, `S3_SECRET_KEY`. install.sh creates it if devops/minio exists. Otherwise: `kubectl create secret generic dify-minio-secret -n dify --from-literal=S3_ACCESS_KEY=... --from-literal=S3_SECRET_KEY=...` |
| **Ingress** | `dify.default.<project>.<domain>`, `dify.<domain>` (Jenkins-style) |

Create the MinIO bucket `dify` in the MinIO console beforehand.

In values.yaml, `k8s_project` and `k8s_domain` are read and substituted by install.sh from e.g. `/root/.k8s/project`.

## Required after install: Model provider and storage in Web UI

Dify Helm install alone does not enable **LLM** or **file storage** in apps. After accessing the Web UI, **install and configure** the following.

### 1. Gemini (model provider) install and config

- **Settings** → **Model Provider** (or plugins/API keys menu).
- Select **Google** / **Gemini** provider, then **Install** or **Configure**.
- Enter the **API key** from [Google AI Studio](https://aistudio.google.com/apikey) and save.
- You can then select **models** (e.g. Gemini 2.0 Flash) from this provider in LLM nodes, question classifiers, etc.

### 2. MinIO S3 Storage Provider install and config

- **Settings** → **Storage** or file storage / **S3 Storage Provider**.
- Select **MinIO** or **S3-compatible** storage provider and install/configure.
- Example inputs:
  - **Endpoint**: `http://minio.devops.svc.cluster.local:9000` (in-cluster MinIO)
  - **Access Key ID** / **Secret Access Key**: from MinIO secret in devops namespace `rootUser` / `rootPassword` (or IAM keys).
  - **Bucket**: `dify` (or your bucket name).
  - **Use HTTPS**: `false` for internal address.
- After saving, Dify file uploads and datasets can use MinIO.

Without the above you may see **api provider not found**, **storage errors**, etc.

### 3. RAG custom tools (CoinTutor RAG / DrillQuiz RAG) — register in UI

To use our RAG backend in app workflows, register the custom tool **once** in the Web UI.

1. **Tools** → **Custom** → **Create custom tool**
2. **Name**: `CoinTutor RAG` (or `DrillQuiz RAG`)
3. **Schema**: **Copy** the full contents of `cointutor/cointutor-rag-openapi.yaml` (or `drillquiz/drillquiz-rag-openapi.yaml`) and **paste** into the schema field
4. **Auth**: None
5. **Save**

Then in workflows, add a **Tool** node and select the tool you created to call RAG `/query`.

**App YAML (CoinTutor.yml) and IDs**: Exported YAML node IDs and `provider_id` vary by environment. In a new Dify: create the custom tool, import `cointutor/CoinTutor.yml`, and **re-select "CoinTutor RAG" in the Tool node** only. See `cointutor/README.md` for the full procedure.

## Install status monitoring

| Command | Description |
|---------|-------------|
| `./status.sh` | One-shot Pod/SVC/PVC/Ingress output |
| `./status.sh watch` | Pod status refresh every 2s (Ctrl+C to stop) |
| `kubectl get pods -n dify -w` | Watch Pods only |
| `kubectl rollout status deployment/dify-api -n dify` | Wait for api Deployment rollout |
| `kubectl logs -n dify -l app.kubernetes.io/name=api -f --tail=50` | Stream api logs |

Set `KUBECONFIG` or `DIFY_NS` (default dify) if needed.

## Connect RAG and chatbot in Web UI (7-4)

**Prerequisite**: Complete **Gemini** and **MinIO S3 Storage Provider** install/config from the “Required after install” section above.

1. **Access**  
   - **Ingress**: `https://dify.default.<project>.<domain>` or `https://dify.<domain>` (after DNS/host setup).  
   - **Port-forward**: If the base URL is empty, redirect/CORS can prevent the UI from loading. When using only port-forward, run  
     `DIFY_BASE_URL=http://localhost:8080 bash install.sh` (or `reinstall`), then  
     `kubectl port-forward svc/dify 8080:80 -n dify` and open **http://localhost:8080** in the browser.  
     Forward to the **dify** service (proxy). Forwarding only **dify-web** changes API address and will not work.  
   Create the admin account on first login.

2. **Knowledge base (vector DB)**  
   - **Settings → Vector database**: If values already set `VECTOR_STORE=qdrant` and `QDRANT_URL`, Dify uses Qdrant.  
   - **Create knowledge base**: In “Knowledge base” create a new one → under **Integration** choose “API” or “Built-in indexer” so Dify can create/use collections in the above Qdrant.  
   - **Reuse existing RAG collection (rag_docs)**: By default Dify may create its own collection with its embedding; to keep using existing `rag_docs`, connect the RAG backend (`rag-backend`’s `/query`) as an “external API” tool.

3. **Data source (MinIO/local)**  
   - **File upload**: When uploading from “Dataset” in Dify, files go to the configured storage (local or S3/MinIO).  
   - **MinIO**: To have files in a MinIO bucket read by Dify, call the MinIO URL from workflow/tool (e.g. “HTTP request”) or configure a “connection” in Dify dataset if supported.

4. **Question→answer flow**  
   - **Create chatbot app**: In “Studio” create a “Chatbot”.  
   - **Use RAG**:  
     - **Option A**: Add “Knowledge base” node → use Dify built-in knowledge base (Qdrant above).  
     - **Option B**: Add “API” under “Tools” → set RAG backend URL (`http://rag-backend.rag.svc.cluster.local:8000/query`) to use existing `rag_docs` search.  
   - Set the prompt to “answer based on knowledge base/tool results” and deploy.

5. **Verify**  
   Ask the chatbot a question and confirm that answers and citations reflect RAG search results.

## Deliverables (Phase 7)

- Chatbot reachable via Dify Web UI
- Vector DB (Qdrant) and optionally MinIO-based RAG and data sources
- Question→answer flow and citation check

## Troubleshooting (known issues)

### Run failed: api provider \<UUID\> not found

**Cause**: After Dify reinstall (uninstall → install) or DB reset, existing apps/workflows still reference the **old model provider (API provider) ID**. That UUID does not exist in the new DB.

**Fix**:

1. In **Settings → Model Provider**, **re-register** the model you use (e.g. Google Gemini) (enter API key and save).
2. Open the **app** that errors → in **Orchestrate (workflow)** open nodes that use a model (LLM, question classifier, etc.) and set **Model** to the **new provider/model** you just registered, then save.
3. If it still errors, **duplicate** the app and in the duplicate workflow re-select model/provider for all nodes, or rebuild the app from scratch.

---

## File layout

| File | Description |
|------|-------------|
| `install.sh` | Project/domain from props, Helm repo, values substitution, Dify install, Ingress. With `reinstall` deletes PVC then reinstalls |
| `status.sh` | Install status (pods/svc/pvc/ingress). With `watch` refreshes in real time |
| `values.yaml` | Images, API/worker env (Qdrant, S3/MinIO), NFS PVC, PostgreSQL/Redis, Weaviate disabled |
| `dify-ingress.yaml` | Jenkins-style Ingress |
| `cointutor/cointutor-rag-openapi.yaml` | CoinTutor RAG OpenAPI schema (paste in UI when creating custom tool) |
| `cointutor/CoinTutor.yml` | CoinTutor app template |
| `drillquiz/drillquiz-rag-openapi.yaml` | DrillQuiz RAG OpenAPI schema (same usage) |
