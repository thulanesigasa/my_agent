# ================================================================
# start-agent.ps1 — Starts both backend (FastAPI) and frontend (Next.js)
# ================================================================

Write-Host ""
Write-Host "  my_agent — Starting all services..." -ForegroundColor Cyan
Write-Host ""

# ── Backend: FastAPI agent on port 8000 ──────────────────────────
Write-Host "  [1/2] Starting backend agent (port 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python start_agent.py" -WindowStyle Normal

Start-Sleep -Seconds 3

# ── Frontend: Next.js on port 3000 ──────────────────────────────
Write-Host "  [2/2] Starting frontend (port 3000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\apps\web'; npm run dev" -WindowStyle Normal

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "  Both services launching in separate windows." -ForegroundColor Green
Write-Host ""
Write-Host "  Backend  ->  http://localhost:8000" -ForegroundColor White
Write-Host "  Frontend ->  http://localhost:3000" -ForegroundColor White
Write-Host ""
