# 🚀 Production Deployment Guide - Autonomous Agent Platform

This guide details how to deploy the containerized platform (FastAPI Agent, Next.js Web UI, Background Worker, and Supabase PostgreSQL `pgvector`) to Railway, Render, or a Ubuntu VPS for 24/7 continuous operation.

---

## Option 1: Railway / Render Deployment

### 1. Repository Setup
Connect your GitHub repository `git@github.com:thulanesigasa/my_agent.git` to Railway or Render.

### 2. Environment Variables
Add the following secrets to your cloud project dashboard:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `GROQ_API_KEY`
- `GEMINI_API_KEY`
- `OPENROUTER_API_KEY`
- `LANGSMITH_TRACING=true`
- `LANGSMITH_API_KEY=your_langsmith_key`

### 3. Deploy Services
- **Backend Agent Service**: Point Dockerfile path to `Dockerfile.agent`, set port to `8000`.
- **Worker Service**: Point Dockerfile path to `Dockerfile.agent`, override start command: `python worker.py`.
- **Frontend Service**: Point Dockerfile path to `Dockerfile.web`, set port to `3000`.

---

## Option 2: Linux VPS (Ubuntu 22.04 LTS)

### 1. Prerequisites & Docker Installation
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose git curl
sudo systemctl enable --now docker
```

### 2. Clone Repository & Environment
```bash
git clone git@github.com:thulanesigasa/my_agent.git
cd my_agent
cp .env.example .env
# Edit .env with production credentials
nano .env
```

### 3. Launch 24/7 Container Stack
```bash
docker-compose up --build -d
```

### 4. Health Check Verification
```bash
curl http://localhost:8000/health
docker-compose ps
```

### 5. SSL & NGINX Reverse Proxy
Install NGINX & Certbot for HTTPS termination:
```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```
Configure NGINX proxy pass for `localhost:3000` (Web) and `localhost:8000` (API/WebSockets).
Execute SSL setup:
```bash
sudo certbot --nginx -d agent.yourdomain.com
```
