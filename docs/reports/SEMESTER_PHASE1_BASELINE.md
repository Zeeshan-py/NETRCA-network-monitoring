# NetRCA Semester Completion Phase 1 — Scope Freeze and Baseline

**Date:** 2026-11-02

**Verdict:** PASS WITH DOCUMENTED LIMITATIONS

**Repository branch:** `main`

## Objective

This phase establishes a verified baseline for the remaining semester work. It does not add product features, change the database schema, seed a remote database, call Gemini, deploy the application, or begin the unified-topology implementation planned for Semester Phase 2.

## Frozen semester scope

The academic deliverable is a controlled network simulation and explainable root-cause analysis system:

1. Define or load a validated network topology.
2. Run the supported topology in the isolated Mininet/Open vSwitch lab.
3. Observe device, interface, link, and connectivity state.
4. Collect validated metrics, logs, and events.
5. Detect anomalies using deterministic rules and supported optional models.
6. Correlate explicitly related evidence into incidents.
7. Analyze topology relationships and rank evidence-backed RCA candidates.
8. Show observed facts, potential impact, limitations, and original evidence in the dashboard.
9. Preserve a reliable synthetic presentation fallback when the live lab is unavailable.

The following are explicitly outside the semester scope: SaaS tenancy, billing, subscriptions, customer onboarding, SSO, enterprise RBAC, Kubernetes, large-scale streaming infrastructure, automated production remediation, and unapproved customer-network discovery.

## Verified architecture baseline

The repository retains separate Next.js frontend, FastAPI backend, PostgreSQL/Supabase persistence, Mininet/Open vSwitch lab, deterministic analysis modules, and documentation. The implemented evidence path is:

```text
topology → monitoring → metrics/logs/events → anomalies → correlation
         → incident → graph context → RCA → impact → explanation → dashboard
```

The current presentation topology is a browser-only synthetic fixture, while the real Mininet topology is `netrca_lab_v1`. Unifying those representations is the principal Semester Phase 2 objective; this phase does not claim they are already the same network.

## Environment verified

| Component | Observed version/state |
| --- | --- |
| Windows Python | 3.14.2 |
| Ubuntu Python | 3.14.4 |
| Node.js | 22.18.0 |
| npm | 11.13.0 |
| WSL | 2.6.3.0; Ubuntu uses WSL2 |
| Mininet | Installed in Ubuntu |
| Open vSwitch | Available and usable by the isolated lab |

## Commands and actual results

### Windows backend

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Result: **106 passed, 25 skipped, 1 warning in 8.65 seconds**. The warning is the existing Starlette/httpx test-client deprecation. Default-off PostgreSQL, Mininet/lab, E2E, and optional dependency paths account for the skipped cases; they are not reported as passes.

### Ubuntu backend

From the Windows repository through Ubuntu WSL2:

```powershell
wsl -d Ubuntu -u root -- bash -lc `
  'cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend" && `
   /home/zeeshan/netrca-venv/bin/python -m pytest -q'
```

Result: **106 passed, 25 skipped, 1 warning in 10.46 seconds**.

### Real Mininet smoke cycle

```powershell
wsl -d Ubuntu -u root -- bash -lc `
  'cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend" && `
   env NETRCA_SIMULATION_ENABLED=true `
   /home/zeeshan/netrca-venv/bin/python -m app.network.cli smoke'
```

Result: **passed**. The lab created `s1`, `s2`, `h1`, `h2`, and `server1` with four expected links. Connectivity before and after reset reported **0% packet loss (6/6 received)**. The command ended with `connected=true`, `connected_after_reset=true`, and `final_state=STOPPED`.

Post-run cleanup verification reported:

- zero Open vSwitch bridges;
- zero network namespaces;
- zero `mnexec` processes.

### Frontend

From `frontend/`:

```powershell
npm test -- --reporter=dot
npm run lint
npm run typecheck
npm run build
```

Results:

- **7 test files and 35 tests passed**;
- ESLint passed;
- Next.js route generation and TypeScript checking passed;
- the optimized Next.js production build passed and generated all static routes.

After verification, `scripts/start-presentation.ps1 -NoBrowser` restarted the local presentation successfully. Both `http://127.0.0.1:8000/api/v1/health` and `http://127.0.0.1:3000` returned HTTP **200**.

## Safety and repository state

- No database migration or database write was performed.
- No live Gemini request was made.
- No external network was scanned or modified.
- Mininet ran only inside the approved Ubuntu WSL2 lab and cleaned up successfully.
- The pre-existing modification to `docs/presentations/NetRCA_Academic_Project_Presentation.pptx` was preserved and excluded from this phase's work.
- The Next.js build temporarily changed generated route references in `frontend/next-env.d.ts`; the file was restored to its pre-test tracked content.

## Known limitations and next action

1. Presentation mode uses a stable frontend fixture rather than live Mininet evidence.
2. The presentation topology and `netrca_lab_v1` use different nodes and identifiers.
3. Database-backed integration suites were not re-run in this baseline phase; the default suite skips them honestly.
4. Live Gemini behavior was not tested and is not required for the semester core.
5. Local-loopback controls are development safeguards, not production user authentication.

The exact next phase is **Semester Phase 2 — Unified Network Scenario Model**: define one validated topology contract and adapters so the backend, Mininet, stored topology, and frontend visualization can represent the same scenario without accepting arbitrary commands.
