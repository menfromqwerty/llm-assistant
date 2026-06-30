# GitHub release checklist for LLM Assistant 2.0.0

Перед публикацией проверьте, что в репозиторий не попали личные данные и локальные сессии.

## 1. Запрещено коммитить

- `.env`
- `.env.*`, кроме `.env.example`
- `security.json`
- `sessions/`
- `.llm_assistant/`
- `backups/`
- `*.llms`
- `*.session.json`
- `*.key`
- `*.pem`
- `*.gguf`
- `*.safetensors`
- `dist/`
- `build/`
- `*.exe`
- `*.zip`

## 2. Проверка статуса Git

```powershell
git status --short
```

В списке не должно быть сессий, ключей, моделей, EXE и ZIP.

## 3. Поиск потенциальных секретов

```powershell
Select-String -Path .\* -Recurse -Pattern "ghp_|github_pat_|sk-|api_key|secret|token|password|BEGIN PRIVATE KEY" -CaseSensitive:$false
```

Допустимы только безопасные упоминания в документации и пустые имена переменных в `.env.example`.

## 4. Очистка локальных артефактов

```powershell
Remove-Item -Recurse -Force .\build, .\dist, .\.pytest_cache, .\__pycache__ -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Include *.pyc,*.pyo,*.spec,*.exe,*.zip,*.llms,security.json -File | Remove-Item -Force
```

## 5. Финальная проверка

```powershell
python -m compileall .
pytest -q
```

## 6. Рекомендуемый тег

```powershell
git tag v2.0.0
git push origin v2.0.0
```
