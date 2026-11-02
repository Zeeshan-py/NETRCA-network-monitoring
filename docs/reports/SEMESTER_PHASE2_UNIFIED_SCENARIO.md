# NetRCA Semester Completion Phase 2 — Unified Network Scenario Model

**Date:** 2026-11-02

**Verdict:** PASS WITH DOCUMENTED LIMITATIONS

**Schema migration:** none

## Objective and result

Phase 2 replaces the independently hard-coded presentation and Mininet topology definitions with one repository-controlled, validated scenario contract. The canonical physical topology, stable identifiers, link endpoints, IP interfaces, and expected Mininet interfaces now originate from `scenarios/netrca_lab_v1.json`.

```text
h1 (10.77.0.11) ─ s1 ─ s2 ─ h2 (10.77.0.12)
                       └──── server1 (10.77.0.20)
```

The presentation continues to use synthetic evidence for reliability, but it overlays that evidence on the same nodes and links used by the actual Mininet lab. It no longer claims a separate router/backup-host topology.

## Architecture

```text
scenarios/netrca_lab_v1.json
       ├── Pydantic NetworkScenario validation
       ├── Python Mininet Topo builder
       ├── live topology → NetworkX graph projection
       ├── local read-only scenario API
       └── TypeScript presentation fixture → dashboard graph
```

Device and link UUIDs use the existing runtime UUID namespace and are verified against the scenario name and key. Consequently, presentation graph IDs match the IDs produced when the real Mininet topology is projected into the graph-analysis model. These runtime IDs do not claim that matching database rows exist.

## Validation and safety

The scenario model rejects:

- unsafe scenario, node, interface, or link names;
- duplicate node keys, names, IDs, IP interfaces, link IDs, link keys, physical links, or interface names;
- unknown endpoints and self-links;
- malformed link keys or keys that do not match their ordered endpoints;
- switches with host addresses or hosts/servers without IPv4 interfaces;
- IDs that differ from the deterministic UUID contract;
- path traversal and unknown scenario names.

Only the repository-controlled canonical scenario is loadable. No upload route, arbitrary command field, controller definition, or host script was added. Mininet remains disabled by default and local-control restrictions remain unchanged.

## API

`GET /api/v1/network/scenario` returns the validated canonical contract without enabling or starting Mininet. It is protected by the existing loopback-only read boundary. Live topology still requires the simulator to be running and remains available through `GET /api/v1/topology`.

## Files created

- `scenarios/netrca_lab_v1.json`
- `backend/app/network/scenario.py`
- `backend/tests/test_network_scenarios.py`
- `frontend/next.config.mjs`
- `docs/guides/network-scenarios.md`
- `docs/reports/SEMESTER_PHASE2_UNIFIED_SCENARIO.md`

## Files updated

- `backend/app/network/topology.py`
- `backend/app/network/mininet_adapter.py`
- `backend/app/network/models.py`
- `backend/app/api/network.py`
- `backend/app/topology/graph.py`
- `frontend/src/lib/presentation-demo.ts`
- `frontend/src/lib/presentation-demo.test.ts`
- `frontend/src/components/dashboard.tsx`
- `scripts/start-presentation.ps1`
- `README.md`
- `docs/guides/INDEX.md`
- `docs/guides/mininet-lab.md`
- `docs/presentations/PRESENTATION_RUNBOOK.md`
- `docs/reports/INDEX.md`

The Next.js build initially rejected the repository-level JSON because Turbopack treats `frontend/` as its default filesystem root. `frontend/next.config.mjs` now explicitly sets the repository root using the supported `turbopack.root` option; the contract is imported directly rather than copied.

The final launcher smoke also reproduced Next.js's current one-time dependency-security reminder: the dev server briefly became ready and then exited to request a retry. `scripts/start-presentation.ps1` now detects only that exact reminder, retries the frontend once, verifies the retry remains alive, and cleans up both child processes if startup fails. This improves presentation reliability but does not replace the separately required dependency security upgrade.

## Tests actually run

| Environment / command | Result |
| --- | --- |
| Windows focused topology/scenario suite | **37 passed**, one existing Starlette/httpx warning |
| Windows full backend suite | **116 passed, 25 skipped**, one existing warning |
| Ubuntu full backend suite | **116 passed, 25 skipped**, one existing warning |
| Ubuntu real Mininet smoke cycle | Passed; 0% packet loss before and after reset; final state `STOPPED` |
| Ubuntu opt-in Mininet integration suite | **2 passed in 4.33 seconds** on the final code |
| Frontend focused presentation tests | **4 passed** |
| Frontend full suite | **7 files, 35 tests passed** |
| Frontend ESLint | Passed |
| Frontend type checking | Passed |
| Frontend optimized production build | Passed after configuring the documented repository root |
| Local presentation launcher and API smoke | Passed; frontend and backend remained available with HTTP 200, scenario endpoint returned 5 nodes and 4 links |

After real Mininet validation, cleanup checks found zero Open vSwitch bridges, zero network namespaces, and zero `mnexec` processes.

The 25 default backend skips are opt-in PostgreSQL, Mininet/lab, E2E, and optional dependency paths. The real Mininet cases relevant to this phase were run separately and passed. No PostgreSQL integration suite was needed because this phase made no database or persistence change.

## Limitations and next step

1. The contract currently contains one controlled topology; runtime user uploads and arbitrary topology creation are intentionally unavailable.
2. Presentation evidence is synthetic and browser-local even though its topology IDs now match the real lab.
3. Live Mininet observations are not automatically persisted as stored topology in this phase.
4. The canonical contract describes physical topology; incident-specific status and evidence remain separate overlays.
5. No live Gemini call, database migration, remote seed, or external network operation was performed.
6. Next.js reports a known dependency-security advisory; this phase does not perform the separately reviewed framework upgrade.

The next phase is **Semester Phase 3 — Network Lifecycle and Visualization**: verify and expose the canonical scenario consistently through start/status/topology/connectivity/stop behavior and the live dashboard source, while retaining stored and synthetic fallbacks.
