# ── Kill any stale backend / frontend processes ──────────────────────────────
Write-Host "Stopping any running backend (port 8000) and frontend (port 3000)..." -ForegroundColor Yellow

$ports = @(8000, 3000)
foreach ($port in $ports) {
    $connections = netstat -ano 2>$null | Select-String ":$port\s" | Select-String "LISTENING"
    foreach ($line in $connections) {
        $pid = ($line -split '\s+')[-1]
        if ($pid -match '^\d+$' -and $pid -ne '0') {
            try { taskkill /PID $pid /F 2>$null | Out-Null; Write-Host "  Killed PID $pid on port $port" -ForegroundColor Gray } catch {}
        }
    }
}

Start-Sleep -Seconds 2
Write-Host "Starting agent..." -ForegroundColor Cyan

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
python start_agent.py
