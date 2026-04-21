@echo off
setlocal
cd /d "%~dp0\.."

if not exist "data\logs" mkdir "data\logs"
set LOG=data\logs\hourly_scan.log
set TS=%DATE% %TIME%

call scripts\hourly_scan.bat
if errorlevel 1 (
    echo [%TS%] cowork_cycle ABORTED - scan failed >> "%LOG%"
    exit /b 1
)

echo [%TS%] cowork_cycle scan OK >> "%LOG%"

echo.
echo ════════════════════════════════════════════════════
echo  Cowork next steps
echo ════════════════════════════════════════════════════
echo.
echo  STEP 1 (token-efficient):
echo    Open Claude Cowork, paste prompts\cowork_decide_prompt.txt,
echo    then ask it to read data\handoff\latest_delta.json
echo    (only new/changed opportunities - smallest token cost).
echo.
echo  STEP 2 (if delta is empty or more context needed):
echo    Ask Cowork to read data\handoff\latest_shortlist.json
echo    (full ranked shortlist).
echo.
echo  STEP 3:
echo    Save Cowork JSON output to data\handoff\cowork_decisions.json
echo.
echo ════════════════════════════════════════════════════

endlocal
