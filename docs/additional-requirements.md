# Additional Requirements and Operational Considerations

Requirements for scaling, operations, security, and tracking in the RAG + Dify demo environment.

---

## 1. Scale management when chat usage grows

| Component | Description | Approach |
|-----------|-------------|----------|
| **Dify API / Worker** | Handles chat requests and workflow execution. High concurrency causes latency/timeouts | Increase `api.replicas`, `worker.replicas` in Helm values. Apply HPA (CPU/memory based). |
| **Dify Queue (Celery/Redis)** | Queue backlog increases wait time | Scale Redis resources/replication and Worker count. Monitor queue depth. |
| **RAG Backend** | Qdrant and embedding API bottleneck under more concurrent `/query` calls | Increase Deployment `replicas`, load balance in front of Service. Apply HPA. |
| **Qdrant** | Vector search load and memory usage | Increase Qdrant Helm resources; horizontal scaling (cluster mode) or dedicated node if needed. |
| **Embedding API (Gemini etc.)** | Per-call quota and rate limits | Batching/caching and/or multiple API key rotation. Combine with Dify-side request limits. |
| **MinIO** | Large file upload/download | Storage capacity and I/O; MinIO distributed setup if needed. |

**Current repo state**: **HPA is applied by default (min=1, max=1)**. RAG: `rag/rag-hpa.yaml` applies HPA to rag-backend, rag-backend-drillquiz, rag-frontend (install.sh [5b/7]). Dify: `dify/dify-hpa.yaml` applies to dify-api, dify-worker (install.sh [5b/5]). All use minReplicas=1, maxReplicas=1, so replicas stay at 1; to scale under load, raise maxReplicas via e.g. `kubectl edit hpa ... -n rag`.

**When scaling (raise maxReplicas)**

- **RAG**: HPA already exists; change `maxReplicas` to 2+ with `kubectl edit hpa rag-backend -n rag`, or `kubectl patch hpa rag-backend -n rag -p '{"spec":{"maxReplicas":5}}'`
- **Dify**: Raise `maxReplicas` in `kubectl edit hpa dify-api -n dify`, `kubectl edit hpa dify-worker -n dify`
- **Metrics server**: HPA (CPU-based) requires metrics-server in the cluster. Without it, `kubectl top pods` does not work and HPA only maintains current replica count.
- **Qdrant**: Single-node by default. Adjust resources in `qdrant-values.yaml`. Horizontal scaling needs cluster mode.

**Other**: Network bandwidth, Ingress Controller resources, DB (PostgreSQL) connections and pooling. Dify uses many DB connections; align API replica count with DB `max_connections`.

---

## 2. Controlling users who ask for unnecessary or sensitive information

| Method | Description |
|--------|-------------|
| **System prompt** | In the Dify workflow LLM node, state rules such as "do not ask for PII or sensitive data", "refuse questions outside knowledge scope". |
| **Input validation** | In custom tools or before the workflow, filter by keyword/pattern (e.g. ID number, email regex) to block or replace. |
| **Policy nodes** | In Dify, use conditional branches (e.g. "question classification") so only allowed topics go to RAG/LLM; others get a fixed guidance message. |
| **Terms and guidelines** | Before or on first chat screen, state that questions must stay within service scope. Link to enforcement (e.g. account limits). |
| **Admin monitoring** | Detect abnormal question patterns/frequency and alert or apply manual sanctions (blacklist, session block). (Can tie to section 5 tracking.) |

**Other**: Dify has role-based access; content-level policy needs to be implemented in workflows or external services. Apply PII masking in logging/storage as well.

---

## 3. Traffic control

| Layer | Method | Status |
|-------|--------|--------|
| **Ingress / LB** | Nginx Ingress `limit-rps`, `limit-connections` to cap RPS and concurrent connections. | ✅ **Applied**: `rag-ingress.yaml` has `limit-rps: "30"`, `limit-connections: "20"` (per IP; 503 when exceeded). |
| **Dify** | Per-app/per-user limits if supported in Dify. Per-API-key limits. | ⚪ Configure in Dify Web UI/app settings. |
| **RAG Backend** | Per-IP rate limit (e.g. slowapi). | ✅ **Applied**: `/query` has slowapi `20/minute` (configurable via env `RATE_LIMIT_QUERY`). |
| **K8s** | ResourceQuota per namespace. | ✅ **Applied**: `rag-resource-quota.yaml` (rag NS: CPU/memory and Pod caps), install.sh [5c/7]. |
| **External APIs** | Quota and monitoring/alerting for Gemini etc. | ⚪ Set up usage monitoring/alerting in operations. |

**Other**: DDoS/abnormal traffic is better handled at WAF or cloud LB level.

---

## 4. Authentication when serving Dify chat in an iframe

| Approach | Description |
|----------|-------------|
| **Dify API Key (per app)** | Issue per-app API keys in Dify. After user login on the parent page, backend maps Dify API key to user session and delivers it. Route chat requests via parent domain backend to minimize key exposure. |
| **SSO / OAuth** | If using Dify Enterprise with SSO, parent site SSO login before iframe, then pass token. Community edition has limited support; expose iframe URL only to users who are authorized to use Dify. |
| **Parent domain auth** | Users log in only on the parent site. Set iframe `src` only for authenticated users (e.g. temporary URL with query/token). Keep Dify internal when possible; parent proxies or uses CORS/cookie policy to restrict. |
| **Token passing** | Parent page passes login session/token to iframe via query or postMessage. Chat client inside iframe includes it in Dify API calls (if Dify accepts user tokens). |
| **Domain and X-Frame-Options** | Set `X-Frame-Options` or CSP `frame-ancestors` on Dify/Ingress to allow only parent domain(s), so only allowed sites can embed the iframe. |

**Other**: Cross-origin iframe limits cookie sharing (SameSite etc.). If chat is "parent backend → Dify API proxy", auth is entirely on the parent and Dify only does server-to-server calls; then user permissions and quotas are managed in the parent backend.

---

## 5. User and request tracking and statistics

| Item | Method |
|------|--------|
| **Dify logs** | Collect request, app ID, user identifier (if set) from API/Worker logs. Aggregate via log pipeline (e.g. Loki, ELK). |
| **Per-app API keys** | Issue separate Dify app API keys per user or group; then aggregate request count and error rate per key in logs/metrics. |
| **RAG Backend logging** | For each `/query`, log timestamp, collection, question length, result count, duration, client identifier (header/API key). |
| **Metrics** | Use Prometheus etc. to collect request count and latency for Dify API/Worker, RAG Backend, Qdrant. Use Grafana for "requests per user/app", "top questions", etc. |
| **User identification** | If Dify receives user info (e.g. API parameters, metadata), use the same identifier in logs and stats. For iframe integration, pass parent site user ID with Dify calls. |

**Other**: Define log retention and masking for privacy; prefer anonymized/aggregate statistics. Design "who asked what" tracking with clear purpose, consent, and minimal collection.

---

## 6. Follow-up (F/U) for user chats

| Method | Description |
|--------|-------------|
| **Store conversation history** | Store sessions and messages in Dify logs/DB or parent system. Add state (e.g. "unresolved"); assign owner and resume on next visit. |
| **Ticket/issue integration** | "Request support" button at chat end creates summary/link in existing ticketing (issue tracker, CRM). Staff follow up with same context. |
| **User mapping** | Map logged-in user ID to conversations so "recent conversations for this user" supports F/U. Pass user_id via Dify app metadata or API parameters. |
| **Alerts and queue** | When "human intervention" is needed (e.g. workflow branch), send webhook/email/Slack and put in internal queue for staff to handle in order. |
| **Export conversation** | User or agent exports chat as PDF/text for email or other channel, then F/U. |

**Other**: Dify has limited built-in "chat F/U" features; managing history and state in the parent system (website backend, CRM, helpdesk) with Dify doing only reply generation is often better. Use Dify API to fetch conversation history and sync to parent if available.

---

## 7. Additional considerations from documentation

| Area | Consideration |
|------|---------------|
| **Cost** | Embedding and LLM API cost scales with chat volume. Usage and budget alerts, caps. |
| **Availability** | If Dify, RAG Backend, Qdrant, or MinIO fails, minimize blast radius (circuit breakers, fallback messages). |
| **Backup and recovery** | Backup policy for Dify DB (PostgreSQL), Qdrant snapshots, MinIO buckets. Document disaster recovery. |
| **Versioning and deployment** | When upgrading Dify or RAG Backend, check compatibility (API schema, workflows). Use blue/green or canary to reduce risk. |
| **Compliance** | Log and conversation retention per privacy regulations and internal policy. Retention period and deletion process. |
| **i18n and accessibility** | Multilingual chat UI and error messages; accessibility (e.g. screen readers). Align tone with parent site when providing iframe. |

---

## 8. Checklist (for adoption)

- [ ] Scale: Dify API/Worker and RAG Backend replicas and HPA; Qdrant and DB resources
- [ ] Control: System prompt, input validation, policy nodes, terms of use
- [ ] Traffic: Ingress rate limit, app/backend rate limit, external API quota monitoring
- [ ] iframe auth: Parent site auth and token passing; X-Frame-Options/CSP
- [ ] Tracking/stats: Log and metric collection, per-user/app aggregation, privacy policy
- [ ] F/U: Conversation storage, ticket integration, user mapping, alerts
- [ ] Cost, availability, backup, compliance
