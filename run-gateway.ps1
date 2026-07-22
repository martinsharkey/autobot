# Start the local LLM gateway on Windows with the virtual environment activated.
# Usage: .\run-gateway.ps1
$ErrorActionPreference = 'Stop'
$venvActivate = Join-Path $PSScriptRoot '.venv\Scripts\Activate.ps1'
if (Test-Path $venvActivate) {
    . $venvActivate
} else {
    Write-Warning "Virtual environment not found at $venvActivate. Start the gateway from an activated env instead."
}
uvicorn main:app --reload --host 0.0.0.0 --port 8000
