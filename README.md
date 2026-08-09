# Autonomous Continuously Learning AI Agent Platform

An enterprise-grade, autonomous, voice-enabled AI agent platform built with **Python (FastAPI + LangGraph)** and **Next.js 15 (App Router + Tailwind CSS + Framer Motion)**. Featuring multi-agent orchestration, continuous memory extraction via Supabase `pgvector`, SiriOrb voice interaction, and multi-LLM fallback architecture.

---

## 🚀 Launch Checklist

- [ ] **1. Environment Configuration**: Copy `.env.example` to `.env` and configure credentials (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`).
- [ ] **2. Database Migration**: Run SQL migration script in `supabase/migrations/001_agent_memory.sql` to enable `pgvector` and create the `langgraph_memory` table with HNSW index.
- [ ] **3. Security Config**: Set `API_KEY_REQUIRED=true` and configure `AGENT_API_KEY` for production deployments.
- [ ] **4. Container Launch**: Execute `docker-compose up --build -d` to launch the multi-container production stack (`agent`, `web`, `worker`, `postgres`).
- [ ] **5. Verification**: Run health check: `curl http://localhost:8000/health`.

---

## 🔒 Production Security Architecture

1. **API Key Authentication**:
   - HTTP routes enforce token verification via `X-API-Key` headers or `api_key` parameters (`verify_api_key`).
   - WebSockets validate token credentials before connection acceptance (`verify_websocket_api_key`).

2. **Abuse Protection & Rate Limiting**:
   - `SlowAPI` rate limiter attached to FastAPI application state with automatic HTTP 429 handler.
   - Endpoint Tiers:
     - Voice & Audio Endpoints (`/ws/audio`): Strict rate limits (10-30 requests/minute).
     - Chat & Approvals (`/api/chat`, `/api/approvals`): Standard rate limits (60 requests/minute).

3. **Human-in-the-Loop Approval Gate**:
   - High-risk operations (such as contract emails, client-facing inquiries, or WhatsApp dispatches) pause graph execution.
   - Pending state is stored securely in Supabase and requires explicit human approval or edits before execution resumes.

4. **HTTP Security Headers**:
   - Enforces `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection`, and `Referrer-Policy`.

---

## 📁 Repository Structure

```
root/
├── .env.example                            # Environment credentials template
├── docker-compose.yml                      # Container orchestrator (agent, web, worker, postgres)
├── Dockerfile.agent                        # Python FastAPI backend image
├── Dockerfile.web                          # Next.js frontend image
├── README.md                               # Launch checklist & security model docs
├── deploy.md                               # Production deployment guide
├── requirements-dev.txt                    # Testing & OpenTelemetry dependencies
├── supabase/
│   └── migrations/
│       └── 001_agent_memory.sql            # Database schema & pgvector HNSW index
├── apps/
│   ├── web/                                # Next.js App Router UI
│   │   ├── app/
│   │   │   ├── page.tsx                    # Main SiriOrb interface
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── ui/siri-orb.tsx             # Interactive SiriOrb component
│   │   │   └── dashboard/approval_queue.tsx# Human-in-the-Loop review dashboard
│   │   └── lib/audio.ts                    # MediaRecorder & Web Audio API manager
│   └── agent/                              # Python LangGraph Backend Service
│       ├── main.py                         # FastAPI entrypoint, HTTP, & WebSockets
│       ├── config.py                       # Pydantic settings & credential validation
│       ├── worker.py                       # 24/7 background task scheduler
│       ├── core/
│       │   ├── graph.py                    # LangGraph StateGraph workflow
│       │   ├── state.py                    # AgentState TypedDict
│       │   ├── memory.py                   # LangGraph BaseStore & pgvector store
│       │   ├── security.py                 # SlowAPI rate limiter & API key auth
│       │   └── telemetry.py                # OpenTelemetry & LangSmith tracing
│       ├── agents/
│       │   ├── triage.py                   # Groq fast intent classification
│       │   ├── drafter.py                  # Gemini 1.5 Pro reasoning & drafting
│       │   ├── learner.py                  # Continuous memory extractor
│       │   └── human_approval.py           # Human review gate node
│       ├── services/
│       │   ├── llm_factory.py              # Multi-model factory (Groq, Gemini, OpenRouter)
│       │   ├── audio_service.py            # Whisper STT & Edge-TTS voice engine
│       │   ├── email_service.py            # Gmail API adapter
│       │   └── whatsapp_service.py         # Twilio WhatsApp adapter
│       └── tests/
│           └── test_agent_flow.py          # Pytest & LangSmith evaluation suite
```

---

## 🤝 License
MIT License. Built for enterprise autonomous agent platforms.
