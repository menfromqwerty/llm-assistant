$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = if (Test-Path ".\.venv\Scripts\python.exe") {
    ".\.venv\Scripts\python.exe"
} else {
    "python"
}

& $python -m pip install --upgrade pyinstaller
& $python -m pip install -r requirements.txt

Remove-Item -Recurse -Force ".\build", ".\dist" -ErrorAction SilentlyContinue
Remove-Item ".\LLM_Assistant.spec" -Force -ErrorAction SilentlyContinue

& $python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --noupx `
  --name "LLM_Assistant" `
  --paths "." `
  --collect-all tkinterdnd2 `
  --collect-all cryptography `
  --collect-submodules llm_assistant `
  ".\main.py"

Write-Host ""
Write-Host "Build complete: $PSScriptRoot\dist\LLM_Assistant.exe" -ForegroundColor Green
