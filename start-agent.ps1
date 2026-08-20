# ================================================================
# start-agent.ps1 — Starts backend, frontend, then opens 3 browser tabs
# ================================================================

Write-Host ""
Write-Host "  my_agent — Starting all services..." -ForegroundColor Cyan
Write-Host ""

# ── Backend: FastAPI agent on port 8000 ──────────────────────────
Write-Host "  [1/3] Starting backend agent (port 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
  "cd '$PSScriptRoot\apps\agent'; python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload" `
  -WindowStyle Normal

# ── Frontend: Next.js on port 3000 ───────────────────────────────
Write-Host "  [2/3] Starting frontend (port 3000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
  "cd '$PSScriptRoot\apps\web'; npm run dev" `
  -WindowStyle Normal

# ── Wait for services to boot ────────────────────────────────────
Write-Host "  [3/3] Waiting for services to boot..." -ForegroundColor Yellow
Start-Sleep -Seconds 8

# ── Open 3 browser tabs ──────────────────────────────────────────
Write-Host "  Opening browser tabs..." -ForegroundColor Green
Start-Process "http://localhost:3000"
Start-Sleep -Milliseconds 400
Start-Process "http://localhost:3000/dashboard"
Start-Sleep -Milliseconds 400
Start-Process "http://localhost:8000"

Write-Host ""
Write-Host "  =============================================" -ForegroundColor Green
Write-Host "  All services running:" -ForegroundColor Green
Write-Host "    Hub       ->  http://localhost:3000" -ForegroundColor White
Write-Host "    Dashboard ->  http://localhost:3000/dashboard" -ForegroundColor White
Write-Host "    Backend   ->  http://localhost:8000" -ForegroundColor White
Write-Host "  =============================================" -ForegroundColor Green
Write-Host ""
