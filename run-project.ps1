$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Virtual environment Python not found at $python"
}

$backendArgs = @(
    "-m", "uvicorn", "backend.app.main:app",
    "--host", "127.0.0.1",
    "--port", "8000"
)

$frontendArgs = @(
    "-m", "streamlit", "run", "frontend\app.py",
    "--server.port", "8501",
    "--server.headless", "true"
)

Start-Process -FilePath $python -ArgumentList $backendArgs -WorkingDirectory $root
Start-Process -FilePath $python -ArgumentList $frontendArgs -WorkingDirectory $root

Write-Host "Backend starting on http://127.0.0.1:8000"
Write-Host "Frontend starting on http://127.0.0.1:8501"
