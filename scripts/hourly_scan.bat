@echo off
setlocal
cd /d "%~dp0\.."

:: ── log setup ────────────────────────────────────────────────────────────────
if not exist "data\logs" mkdir "data\logs"
set LOG=data\logs\hourly_scan.log
set TS=%DATE% %TIME%
echo [%TS%] hourly_scan START >> "%LOG%"

:: ── venv check ───────────────────────────────────────────────────────────────
if not exist ".venv\Scripts\python.exe" (
    echo [%TS%] ERROR: .venv not found >> "%LOG%"
    echo.
    echo ERROR: .venv\Scripts\python.exe not found.
    echo Run these commands to create it:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -e ".[dev]"
    echo.
    exit /b 1
)

:: ── run export-shortlist ─────────────────────────────────────────────────────
.venv\Scripts\python.exe -m polyclaude_bot.cli export-shortlist ^
    --limit 20 ^
    --top-n 5 ^
    --min-liquidity 10000 ^
    --max-spread 0.05 ^
    --min-abs-edge-bps 50
set RC=%ERRORLEVEL%

if %RC% neq 0 (
    echo [%TS%] ERROR: export-shortlist exited %RC% >> "%LOG%"
    echo ERROR: export-shortlist failed (exit %RC%)
    exit /b %RC%
)

:: ── verify output files ───────────────────────────────────────────────────────
set MISSING=0
if not exist "data\handoff\latest_shortlist.csv"  set MISSING=1
if not exist "data\handoff\latest_shortlist.json" set MISSING=1
if not exist "data\handoff\latest_delta.json"     set MISSING=1

if %MISSING% neq 0 (
    echo [%TS%] ERROR: one or more handoff files missing >> "%LOG%"
    echo ERROR: handoff output files not found in data\handoff\
    exit /b 1
)

echo [%TS%] hourly_scan OK >> "%LOG%"
echo Handoff files verified in data\handoff\
endlocal
