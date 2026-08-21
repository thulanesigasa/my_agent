# 📖 Production Operational Runbook - Autonomous Agent Platform

This operational runbook provides step-by-step procedures for handling production incidents, API rate limits, checkpointer session resets, emergency overrides, and credential rotation for the autonomous AI agent platform.

---

## 🚨 Incident Response Matrix

| Incident Type | Severity | Primary Cause | Mitigation Procedure |
| :--- | :--- | :--- | :--- |
| **API Provider Outage** | P1 | Groq or Gemini API offline | OpenRouter fallback auto-triggers; switch model in `.env` |
| **Stuck LangGraph Execution** | P2 | Deadlocked node or unhandled tool error | Execute session reset API call or restart worker container |
| **Database Connection Loss** | P1 | Supabase pgvector connection drop | Verify `SUPABASE_URL` credentials & restart agent cluster |
| **Memory Extraction Leak** | P3 | High noise indexed in `langgraph_memory` | Run cleanup SQL query in Supabase |

---

## 🛠️ Step-by-Step Operating Procedures

### 1. Handling API Provider Outages & Fallback Manual Override
The backend features an automated fallback mechanism (`LLMFactory` in `apps/agent/services/llm_factory.py`).
If Groq Llama 3.3 70B fails:
1. The engine automatically catches the error and routes the request to OpenRouter (`anthropic/claude-3-haiku`).
2. To force a global fallback to OpenRouter without restarting:
   ```bash
   # Update environment setting in .env
   GROQ_API_KEY=""
   # Reload Uvicorn worker process
   ```

---

### 2. Clearing Stuck LangGraph State Sessions
If a user thread gets stuck in a pending loop or unhandled state:
```bash
# Query active pending approvals via API
curl http://localhost:8000/api/approvals

# Reject or reset stuck thread_id
curl -X POST http://localhost:8000/api/approvals/stuck_thread_id/action \
  -H "Content-Type: application/json" \
  -d '{"action": "reject"}'
```

---

### 3. Emergency Human Override & System Shutdown
To halt automated external tool executions (emails, WhatsApp dispatches):
1. Set `API_KEY_REQUIRED=true` and change `AGENT_API_KEY` in `.env`.
2. Stop background worker process:
   ```bash
   docker-compose stop worker
   ```

---

### 4. Zero-Downtime API Key Rotation
To rotate `GROQ_API_KEY`, `GEMINI_API_KEY`, or `SUPABASE_SERVICE_ROLE_KEY`:
1. Update secrets in your cloud provider environment dashboard (Railway/Render) or `.env`.
2. Perform rolling container restart:
   ```bash
   docker-compose up -d --no-deps --build agent worker
   ```

---

## 📊 Observability & Monitoring Metrics
- **Health Check Endpoint**: `GET /health/detailed`
- **LangSmith Dashboard**: Check execution traces under `autonomous-agent-platform` project.
