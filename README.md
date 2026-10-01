# FlowForge

A distributed workflow orchestration engine.

> **Status:** Phase 1 — project foundation.

## Local development

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn app.main:app --app-dir backend --reload