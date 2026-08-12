# Autonomous Continuously Learning AI Agent Platform

An enterprise-grade, autonomous, voice-enabled AI agent platform representing **T.s Industries** (led by Pharez / Thulane). Built with **Python (FastAPI + LangGraph)** and **Next.js 15 (App Router + Tailwind CSS + Framer Motion)**. Featuring multi-agent orchestration, continuous memory extraction via Supabase `pgvector`, SiriOrb voice interaction, dynamic runtime knowledge reading, procedural rules & SOP skills, dynamic risk evaluation with Human-in-the-Loop breakpoints, real-time Gmail Pub/Sub webhooks, and structured CRM sales pipeline tracking.

---

## 🚀 Launch Checklist

- [ ] **1. Environment Configuration**: Copy `.env.example` to `.env` and configure credentials (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `WEBHOOK_SECRET`).
- [ ] **2. Database Migrations**: Run SQL migration scripts in `supabase/migrations/001_agent_memory.sql` (pgvector store) and `002_crm_tables.sql` (clients & project sales pipeline).
- [ ] **3. Security Config**: Set `API_KEY_REQUIRED=true` and configure `AGENT_API_KEY` for production deployments.
- [ ] **4. Container Launch**: Execute `docker-compose up --build -d` to launch the multi-container production stack (`agent`, `web`, `worker`, `postgres`).
- [ ] **5. Verification**: Run health check: `curl http://localhost:8000/health`.

---

## 🎙️ Hands-Free Agent Terminal Launcher (`start agent`)

Kick-start the agent listener instantly using custom terminal commands or Python:

```bash
# Type directly in Command Prompt / PowerShell:
start agent

# OR run python:
python start_agent.py
```
- **Console Response**: Responds with a vibrant green **`[+] AGENT ACTIVE`** status banner.
- **Dual Activation Triggers**:
  1. **👏 Hand Clap**: Single sharp sound peak trigger.
  2. **🗣️ Voice Command**: Saying **`"Agent"`** into your microphone.
- **Automated Actions**:
  1. Boots/ensures FastAPI backend server (`http://localhost:8000`).
  2. Boots/ensures Next.js web application frontend (`http://localhost:3000`).
  3. Launches or focuses application browser tabs without duplicate tab creation.

---

## 🔒 Production Security & Risk Architecture

1. **Dynamic Risk Evaluation & Guardrails**:
   - Evaluates intended agent actions against `memory/guardrails.md` rules into three risk levels:
     - **LOW STAKES (Auto-Approve)**: Internal searches, lead browsing, public QA, drafting notes.
     - **HIGH STAKES (Requires Human Approval)**: External client emails, issuing quotes, modifying memory/rules, sending WhatsApp messages.
     - **FORBIDDEN (Halt Execution)**: Payment processing, secret key/password sharing, spamming.
2. **Native LangGraph Breakpoints**:
   - Compiled with `interrupt_before=["human_approval"]`. High-risk threads pause execution state automatically until explicitly approved via the Next.js dashboard.
3. **API Key & Webhook Security**:
   - HTTP routes enforce token verification via `X-API-Key` headers.
   - Pub/Sub webhooks validate `X-Goog-PubSub-Token` headers.
4. **Abuse Protection & Rate Limiting**:
   - `SlowAPI` rate limiter attached to FastAPI state with automatic HTTP 429 handlers.

---

## 📁 Repository Structure

```
root/
├── .env.example                            # Environment credentials template
├── docker-compose.yml                      # Container orchestrator (agent, web, worker, postgres)
├── Dockerfile.agent                        # Python FastAPI backend container image
├── Dockerfile.web                          # Next.js frontend container image
├── README.md                               # System documentation & structure overview
├── RUNBOOK.md                              # System operational runbook
├── deploy.md                               # Production deployment guide
├── requirements-dev.txt                    # Testing & OpenTelemetry dependencies
├── knowledge/                              # Dynamic Company Knowledge Base (.md)
│   ├── about_us.md                         # Company identity, leadership, website, directives
│   ├── services_and_stack.md               # Web, mobile, backend & AI tech stack details
│   ├── brand_voice.md                      # Tone guidelines & formatting rules
│   └── learned_insights.md                 # Learned business facts & insights
├── memory/                                 # Procedural & Security Memory Store
│   ├── rules.md                            # Unbreakable business rules (discount floor, quotes)
│   ├── guardrails.md                       # Security definitions (LOW, HIGH, FORBIDDEN)
│   └── procedures/                         # Standard Operating Procedures (SOP skills)
│       └── generate_quote.md               # Step-by-step quote generation skill
├── supabase/
│   └── migrations/
│       ├── 001_agent_memory.sql            # Vector store schema & pgvector HNSW index
│       └── 002_crm_tables.sql            # Clients & Projects CRM sales pipeline schema
├── apps/
│   ├── web/                                # Next.js 15 App Router Web UI
│   │   ├── app/
│   │   │   ├── page.tsx                    # Gemini UI, SiriOrb voice mode, white orb overlay
│   │   │   └── layout.tsx                  # Root layout & font configuration
│   │   ├── components/
│   │   │   ├── app-shell.tsx               # 150ms sidebar collapse layout shell
│   │   │   ├── dashboard.tsx               # Efferd flat 1px grid layout & step-line chart
│   │   │   ├── chat/                       # Chat feed & voice interaction components
│   │   │   ├── dashboard/                  # Approval queue & memory inspector views
│   │   │   └── ui/siri-orb.tsx             # Interactive SiriOrb component
│   │   └── lib/
│   │       ├── api.ts                      # Strongly typed API client & memory queries
│   │       └── audio.ts                    # MediaRecorder & Web Audio API manager
│   └── agent/                              # Python LangGraph Backend Service
│       ├── main.py                         # FastAPI entrypoint, HTTP, WebSockets, & lifecycles
│       ├── config.py                       # Pydantic settings & credential validation
│       ├── scheduler.py                    # APScheduler active/sleep cycles & 2-min polling worker
│       ├── worker.py                       # 24/7 background worker entrypoint
│       ├── requirements.txt                # Production backend Python dependencies
│       ├── core/
│       │   ├── graph.py                    # LangGraph StateGraph & native interrupt breakpoints
│       │   ├── state.py                    # AgentState schema definition
│       │   ├── memory.py                   # Supabase pgvector memory store manager
│       │   ├── security.py                 # SlowAPI rate limiter & auth handlers
│       │   └── telemetry.py                # OpenTelemetry & tracing initializers
│       ├── agents/
│       │   ├── triage.py                   # Intent classification & context router
│       │   ├── risk_evaluator.py           # Guardrails evaluator node (LOW, HIGH, FORBIDDEN)
│       │   ├── drafter.py                  # Gemini 1.5 Pro reasoning & response node
│       │   ├── knowledge_manager.py        # Autonomous knowledge writer node
│       │   ├── skill_learner.py            # Procedural skill & SOP learner node
│       │   ├── human_approval.py           # Human-in-the-loop review gate node
│       │   ├── outreach_agent.py           # Multi-node lead discovery & outreach sub-graph
│       │   └── learner.py                  # Continuous vector memory extractor
│       ├── tools/
│       │   ├── knowledge_tools.py          # Dynamic runtime knowledge base reader/writer
│       │   ├── procedural_tools.py         # Unbreakable rules loader & skill fetcher
│       │   ├── admin_tools.py              # Memory unlearn & sent email history tools
│       │   └── lead_finder.py              # Business search & email enrichment tools
│       ├── services/
│       │   ├── llm_factory.py              # Multi-model factory (Groq, Gemini, OpenRouter)
│       │   ├── crm_service.py              # Supabase client & project pipeline CRM layer
│       │   ├── notification_service.py     # Priority email & web push alert service
│       │   ├── report_service.py           # Multi-sheet Excel weekly report generator
│       │   ├── audio_service.py            # Whisper STT & Edge-TTS voice engine
│       │   ├── email_service.py            # Gmail API integration adapter
│       │   └── whatsapp_service.py         # Twilio WhatsApp adapter
│       ├── routers/
│       │   ├── health.router               # System health endpoints
│       │   └── webhooks.py                 # Real-time Google Cloud Pub/Sub webhooks
│       └── tests/
│           └── test_agent_flow.py          # Pytest & workflow test suite
```

---

## ⚖️ Copyright & License

**Copyright © 2026 T.s Industries. All Rights Reserved.**

This software and associated documentation files are **proprietary and confidential**. Unauthorized copying, distribution, modification, or public display of this software, via any medium, is strictly prohibited without the express written permission of T.s Industries (Pharez / Thulane).
