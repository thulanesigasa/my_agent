# ── Kill any stale backend / frontend processes ──────────────────────────────
Write-Host "Stopping any running backend (port 8000) and frontend (port 3000)..." -ForegroundColor Yellow

$ports = @(8000, 3000)
foreach ($port in $ports) {
    $connections = netstat -ano 2>$null | Select-String ":$port\s" | Select-String "LISTENING"
    foreach ($line in $connections) {
        $procId = ($line -split '\s+')[-1]
        if ($procId -match '^\d+$' -and $procId -ne '0') {
            try { taskkill /PID $procId /F 2>$null | Out-Null; Write-Host "  Killed PID $procId on port $port" -ForegroundColor Gray } catch {}
        }
    }
}

# Stop any orphan Node workers holding file locks on .next
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Purge .next cache with retries to handle Windows file locks
$nextPath = "apps/web/.next"
if (Test-Path $nextPath) {
    for ($i = 0; $i -lt 5; $i++) {
        try {
            Remove-Item -Recurse -Force $nextPath -ErrorAction Stop
            Write-Host "  Purged stale .next build cache." -ForegroundColor Gray
            break
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
}

Write-Host "Starting agent..." -ForegroundColor Cyan

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
python start_agent.py
