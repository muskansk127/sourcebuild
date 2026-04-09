@echo off
setlocal
cd /d "%~dp0"

if "%PORT%"=="" set PORT=5000
set BASE=http://127.0.0.1:%PORT%

echo Checking app routes on %BASE%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ProgressPreference='SilentlyContinue';" ^
  "$urls=@('%BASE%/','%BASE%/about','%BASE%/login','%BASE%/health');" ^
  "foreach($u in $urls){" ^
  "  try { $r=Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 8; Write-Host ($u + ' -> ' + $r.StatusCode) }" ^
  "  catch { Write-Host ($u + ' -> ERROR: ' + $_.Exception.Message) }" ^
  "}"

echo.
echo Expected: 200 for all routes (health may be 503 if DB is intentionally unavailable and fallback is off).
pause
endlocal
