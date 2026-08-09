# Autonomous Continuously Learning AI Agent Platform

An enterprise-grade, autonomous, voice-enabled AI agent platform built with **Python (FastAPI + LangGraph)** and **Next.js 15 (App Router + Tailwind CSS + Framer Motion)**. Featuring multi-agent orchestration, continuous memory extraction via Supabase `pgvector`, SiriOrb voice interaction, and multi-LLM fallback architecture.

---

## 🌟 Key Architecture & Highlights

- **Frontend (`apps/web`)**: Next.js App Router, TypeScript, Framer Motion interactive 3D `SiriOrb`, real-time WebSocket communication, audio recorder, chat feed, memory vault inspector, and Human-in-the-Loop approval dashboard.
- **Backend (`apps/agent`)**: FastAPI with WebSockets, LangGraph state graph machine (`TriageNode` via Groq Llama 3.3 70B -> `DrafterNode` via Gemini 1.5 Pro -> `LearnerNode` memory extractor -> `OutputDispatcher`).
- **Memory Engine**: Supabase PostgreSQL + `pgvector` for semantic recall of past conversations and automated user preference indexing.
- **Multi-Model Orchestration**:
  - **Groq API**: Llama 3.3 70B (Fast intent triage & routing) + Whisper (Speech-to-Text).
  - **Google AI Studio**: Gemini 1.5 Pro (Deep drafting, long-context reasoning).
  - **OpenRouter API**: Seamless fallback gateway.
  - **Edge-TTS / Web Audio API**: Low-latency neural text-to-speech audio streaming.
- **Tools & Approvals**: Gmail & WhatsApp integration adapters with safety gates for high-risk action approval.

---

## 📁 Repository Structure

```
root/
├── apps/
│   ├── web/                    # Next.js App Router UI
│   │   ├── app/
│   │   │   ├── api/agent/      # API route proxy handlers
│   │   │   ├── page.tsx        # Voice & Chat interface + Agent Dashboard
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── ui/siri-orb.tsx # Dynamic interactive 3D Canvas SiriOrb component
│   │   │   ├── chat/           # Chat Feed & Memory Viewer
│   │   │   └── dashboard/      # LangGraph state monitor & tool approval panel
│   │   ├── lib/
│   │   │   ├── utils.ts        # Helper utilities
│   │   │   └── audio.ts        # Web Audio API recorder & decoder helpers
│   │   └── public/
│   └── agent/                  # Python LangGraph Backend Service
│       ├── main.py             # FastAPI entrypoint & WebSocket handler
│       ├── config.py           # Environment settings & API credentials
│       ├── core/
│       │   ├── graph.py        # LangGraph state machine & router flow
│       │   ├── state.py        # TypedDict AgentState definition
│       │   └── memory.py       # Supabase vector store & checkpointer
│       ├── agents/
│       │   ├── triage.py       # Groq fast triage agent node
│       │   ├── drafter.py      # Gemini drafting & reasoning node
│       │   └── learner.py      # Memory extractor & indexer node
│       ├── services/
│       │   ├── llm_factory.py  # Groq, Gemini, OpenRouter provider factory
│       │   ├── audio_service.py# Groq Whisper STT & Edge-TTS speech engine
│       │   ├── email_service.py# Gmail adapter
│       │   └── whatsapp_service.py # WhatsApp / Twilio adapter
│       └── requirements.txt
├── docker-compose.yml          # Containerized setup
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.11+** installed
- **Node.js 18+** & `npm` / `pnpm`
- **Docker & Docker Compose** (optional for local database & full container stack)
- API Keys for **Supabase**, **Groq**, **Google AI Studio (Gemini)**

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in your credentials:
- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
- `GROQ_API_KEY`
- `GEMINI_API_KEY`
- `OPENROUTER_API_KEY` (Optional fallback)

### 3. Backend Setup (`apps/agent`)
```bash
cd apps/agent
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Backend API will run at `http://localhost:8000` with WebSocket endpoint at `ws://localhost:8000/ws/agent`.

### 4. Frontend Setup (`apps/web`)
```bash
cd apps/web
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 🐳 Docker Deployment
To launch the entire platform (PostgreSQL pgvector, Python Agent, and Next.js frontend) with Docker:
```bash
docker-compose up --build
```

---

## 🔒 Supabase Schema Setup (SQL Script)
Run this SQL snippet in your Supabase SQL Editor to prepare `pgvector`:
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS agent_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS agent_memories_embedding_idx 
ON agent_memories USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

---

## 🤝 License
MIT License. Built for autonomous agent scaling.
