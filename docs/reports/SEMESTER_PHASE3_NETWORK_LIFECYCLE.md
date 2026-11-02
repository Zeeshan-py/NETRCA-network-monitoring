# NetRCA Semester Completion Phase 3 — Network Lifecycle and Visualization

**Date:** 2026-11-02

**Verdict:** PASS WITH DOCUMENTED LIMITATIONS

**Schema migration:** none

## Objective and result

Phase 3 connects the canonical `netrca_lab_v1` scenario to an operator-facing lifecycle in the dashboard. A local operator can start the fixed Mininet lab, inspect its live graph, run measured host connectivity, reset the topology, and stop it without entering arbitrary commands or changing the scenario.

```text
Dashboard control
      │ local-control POST
      ▼
FastAPI lifecycle manager ──► Mininet / Open vSwitch
      │                              │
      ├── status polling             ├── actual nodes and interfaces
      ├── connectivity result        └── measured ping connectivity
      └── live NetworkX graph ──► interactive topology canvas
```

The browser distinguishes the live Mininet source from stored PostgreSQL topology. Presentation mode remains a synthetic, browser-only fallback and deliberately hides the real Mininet controls.

## Implemented behavior

- Added typed frontend calls for start, stop, reset, and connectivity-test routes.
- Every control call uses `POST` and the existing `X-NetRCA-Local-Control: 1` header.
- Added a responsive Mininet lifecycle panel to the Topology page.
- Controls are enabled only for valid states; duplicate or conflicting actions are blocked in the UI and still rejected by the backend.
- A bounded poll follows backend `202`/transitional responses until the operation settles or 60 seconds elapse.
- Successful lifecycle operations refresh status and the live topology graph automatically.
- Connectivity results report the actual host count and measured packet-loss percentage.
- Disabled or unavailable simulation states provide an actionable Ubuntu/WSL2 message.
- The live API integration test verifies the stable scenario identifiers through the browser-facing graph endpoint.

## Safety boundaries retained

- Simulation remains disabled by default.
- The backend must run on loopback in the approved Ubuntu lab with one worker.
- Control routes require both a loopback peer and the local-control header.
- Configured browser origins must also be local.
- No route accepts shell commands, uploaded topology definitions, arbitrary interfaces, or arbitrary probe targets.
- No database migration, database write, Gemini request, external scan, Docker operation, or remote deployment was performed.
- Browser presentation mode cannot start or modify Mininet.

## Files created

- `frontend/src/components/network-lab-controls.tsx`
- `frontend/src/components/network-lab-controls.test.tsx`
- `docs/reports/SEMESTER_PHASE3_NETWORK_LIFECYCLE.md`

## Files updated

- `frontend/src/lib/api.ts`
- `frontend/src/lib/api.test.ts`
- `frontend/src/components/dashboard.tsx`
- `frontend/src/app/page.test.tsx`
- `frontend/src/app/globals.css`
- `backend/tests/test_network.py`
- `backend/tests/test_mininet_integration.py`
- `docs/guides/mininet-lab.md`
- `docs/presentations/PRESENTATION_RUNBOOK.md`
- `docs/reports/INDEX.md`
- `README.md`

## Verification

| Environment / command | Actual result |
| --- | --- |
| Windows focused network, scenario, and graph tests | **31 passed**, one existing Starlette/httpx warning |
| Windows full backend suite | **116 passed, 26 skipped**, one existing warning |
| Ubuntu full backend suite | **116 passed, 26 skipped**, one existing warning |
| Ubuntu opt-in real Mininet suite | **3 passed in 7.70 seconds**, one existing warning |
| Frontend unit/component suite | **8 files, 42 tests passed** |
| Frontend ESLint | Passed |
| Frontend TypeScript checking | Passed |
| Frontend optimized build | Passed after the documented one-time security-advisory retry |
| `git diff --check` | Passed |

The 26 default skips are the explicit PostgreSQL, Mininet, E2E, and optional-dependency paths. The three relevant Mininet cases were run separately as root in Ubuntu and passed. That opt-in suite starts Mininet, validates the canonical topology through both the manager and FastAPI, measures connectivity, stops the lab, and exercises partial-start cleanup. Post-test inspection showed no Open vSwitch bridges, network namespaces, or `mnexec` processes.

## Demonstration workflow

1. Start the backend as root inside Ubuntu WSL2 with simulation enabled, one worker, and local CORS for port 3000.
2. Start the frontend from PowerShell with presentation mode disabled.
3. Open **Topology** and select **Start lab**.
4. Show five live nodes and four links, then select **Test connectivity** and explain the measured packet loss.
5. Select a device or link to demonstrate interactive topology inspection.
6. Select **Reset topology** if a clean state is needed.
7. Always select **Stop lab** before ending the demonstration.

## Limitations and next step

1. The dashboard controls one repository-defined scenario; user-defined topology editing remains intentionally unavailable.
2. Mininet and Open vSwitch still require the prepared Ubuntu WSL2 environment and elevated Linux privileges.
3. Live runtime identifiers align with the canonical scenario but do not claim corresponding database rows.
4. The dashboard polls after explicit actions; it is not a continuous WebSocket telemetry stream.
5. The installed Next.js version reports a dependency-security advisory and should be upgraded in a separate reviewed change.

The next phase is **Semester Phase 4 — Evidence Collection Demonstration**: collect and display a small, controlled observation set from the running canonical lab while retaining explicit source, timestamp, and uncertainty boundaries.
