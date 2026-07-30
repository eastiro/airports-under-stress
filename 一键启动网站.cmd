@echo off
setlocal

set "SITE_URL=http://localhost:3000/"
set "WEB_DIR=%~dp0web"

if not exist "%WEB_DIR%\package.json" (
  echo Cannot find the website folder: %WEB_DIR%
  pause
  exit /b 1
)

rem If the website is already running, only open it.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing '%SITE_URL%' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1"
if not errorlevel 1 (
  start "" "%SITE_URL%"
  exit /b 0
)

rem Start the development server in a separate window.
start "Airports Under Stress Server" cmd.exe /k "cd /d ""%WEB_DIR%"" && npm.cmd run dev"

rem Wait until the site responds, then open the browser.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$deadline = (Get-Date).AddSeconds(30); do { try { $r = Invoke-WebRequest -UseBasicParsing '%SITE_URL%' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; Start-Sleep -Milliseconds 500 } while ((Get-Date) -lt $deadline); exit 1"
if errorlevel 1 (
  echo The website did not start within 30 seconds. Check the server window for details.
  pause
  exit /b 1
)

start "" "%SITE_URL%"
endlocal
