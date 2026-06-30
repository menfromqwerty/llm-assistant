# Clean local generated/private files before GitHub commit.
# Run from project root:
# powershell -ExecutionPolicy Bypass -File .\scripts\clean_for_github.ps1

$ErrorActionPreference = "SilentlyContinue"

Remove-Item -Recurse -Force ".\build", ".\dist", ".\.pytest_cache", ".\.mypy_cache", ".\.ruff_cache", ".\htmlcov", ".\.llm_assistant", ".\sessions", ".\backups"

Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -File -Include "*.pyc", "*.pyo", "*.spec", "*.exe", "*.msi", "*.zip", "*.llms", "*.session.json", "security.json", ".env" | Remove-Item -Force

Write-Host "Cleaned local GitHub-unsafe artifacts. Check git status before commit."
