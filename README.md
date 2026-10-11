# NetRCA

NetRCA is an AI-assisted network root cause analysis and incident response project for a controlled Mininet simulation. The system is being developed in phases; the architecture and requirements are in [`Instruction/`](Instruction/).

## Current scope

Phase 1 provides a FastAPI application with a versioned API health endpoint and a Next.js application shell that checks that endpoint. The health response describes the API process only. The UI contains no live network metrics or incident data.

```
backend/    FastAPI app, configuration, and pytest tests
frontend/   Next.js app, API client, styling, and Vitest tests
Instruction/ Original project specifications and design preview
```

## Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer and npm
- Git for version control

Mininet needs Linux networking support; WSL2 with Ubuntu is recommended for its later setup phase. Mininet is not needed to run Phase 1 on Windows.

## Backend

In PowerShell, from the repository root:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On Linux or WSL2, activate with `source .venv/bin/activate` and copy the example file with `cp .env.example .env`.

- API health: `http://localhost:8000/api/v1/health`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`

Run backend tests from `backend/` with `python -m pytest`.

## Frontend

In a second terminal, from the repository root:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open `http://localhost:3000`. For a production build, run `npm run build`, then `npm start`. Run checks with `npm test`, `npm run typecheck`, and `npm run lint`.

## Configuration

The backend reads `backend/.env` or process environment variables. The frontend reads `frontend/.env.local`. The examples contain only local development values.

| Variable | Used by | Purpose |
| --- | --- | --- |
| `NETRCA_CORS_ORIGINS` | Backend | Comma-separated browser origins allowed to call the API; set to the frontend origin |
| `NETRCA_LOG_LEVEL` | Backend | Application log level |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend | Browser-accessible API base URL, including `/api/v1` |

If the frontend runs on a different origin, update `NETRCA_CORS_ORIGINS` accordingly. Restart the frontend after changing its environment file. Never put future Gemini keys or Supabase service credentials in a `NEXT_PUBLIC_` variable.

## Limitations

Network simulation, database storage, monitoring, anomaly detection, incident management, RCA, Gemini, authentication, and fault injection are planned for later phases. An API connection indicator confirms only that the FastAPI health endpoint responded. It does not indicate network health.
# NETRCA-network-monitoring
