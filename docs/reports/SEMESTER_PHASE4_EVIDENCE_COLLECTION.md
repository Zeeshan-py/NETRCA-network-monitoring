# NetRCA Semester Completion Phase 4 — Evidence Collection Demonstration

**Date:** 2026-11-02

**Verdict:** PASS WITH DOCUMENTED LIMITATIONS

**Schema migration:** none

## Objective and result

Phase 4 exposes a small, controlled set of actual observations from the running canonical Mininet lab in the dashboard. It displays timestamped interface counters, interface and link state, collection limitations, and one bounded host-to-host probe without representing ephemeral observations as stored history.

```text
running netrca_lab_v1
      ├── read-only interface snapshot ──► timestamped dashboard table
      └── bounded known-host probe ──────► loss, packets and average latency

stored PostgreSQL evidence remains a separate section and is not changed
```

## Implemented behavior

- Added a responsive **Live evidence capture** panel to the Evidence page.
- Captures the existing read-only `GET /api/v1/network/monitoring` snapshot on explicit request.
- Displays observation time, topology, runtime state, collection completeness, counter semantics, interface state, cumulative byte/packet counters, errors, and observed link state.
- Preserves unavailable counters as **Unavailable** and shows backend error codes instead of inventing zero values.
- Builds the probe selector only from HOST and SERVER names returned by the validated live snapshot.
- Runs the existing bounded `POST /api/v1/network/monitoring/probe` operation with two packets and a two-second per-packet timeout.
- Displays source, destination, timestamp, reachability, packets sent/received, measured loss, average latency, and any error code.
- Labels route reachability as distinct from long-term device uptime.
- Labels live observations as **ephemeral** and explicitly states that this panel does not write to PostgreSQL.
- Keeps presentation-mode observations labeled as a synthetic fixture and hides live capture/probe controls.
- Keeps stored metrics, logs, and events visibly separate below the runtime panel.

## Data integrity and safety

- The frontend sends no command, IP address, interface name, packet count, or timeout supplied as free-form text.
- Probe endpoints are chosen from the known hosts returned by the current canonical snapshot; backend allow-list validation remains authoritative.
- Monitoring uses shell-free argument arrays inside Mininet namespaces and retains its existing execution timeouts.
- Partial snapshots retain their `PARTIAL` state and explicit limitations.
- Missing counters remain missing; cumulative counters are not presented as throughput rates.
- No pipeline persistence route is called by this phase.
- No database migration, remote database write, Supabase seed, Gemini request, Docker operation, or external network scan was performed.

## Files created

- `frontend/src/components/live-evidence-capture.tsx`
- `frontend/src/components/live-evidence-capture.test.tsx`
- `docs/reports/SEMESTER_PHASE4_EVIDENCE_COLLECTION.md`

## Files updated

- `frontend/src/lib/api.ts`
- `frontend/src/lib/api.test.ts`
- `frontend/src/components/dashboard.tsx`
- `frontend/src/app/page.test.tsx`
- `frontend/src/app/globals.css`
- `backend/tests/test_monitoring_integration.py`
- `docs/guides/network-monitoring.md`
- `docs/presentations/PRESENTATION_RUNBOOK.md`
- `docs/reports/INDEX.md`
- `README.md`

## Verification

The real Ubuntu test starts the canonical lab, captures the snapshot through the
internal manager and FastAPI, runs bounded probes, checks source, timestamp, and
uncertainty fields, stops the lab, and verifies cleanup.

| Check | Command | Result |
|---|---|---|
| Focused Windows monitoring and pipeline tests | `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_monitoring.py tests/test_pipeline.py tests/test_monitoring_integration.py` | **12 passed, 2 skipped**, 1 existing dependency warning |
| Full Windows backend suite | `.\\.venv\\Scripts\\python.exe -m pytest -q` | **116 passed, 27 skipped**, 1 existing dependency warning |
| Full Ubuntu WSL2 backend suite | `~/netrca-venv/bin/python -m pytest -q` | **116 passed, 27 skipped**, 1 existing dependency warning |
| Real Ubuntu Mininet monitoring API integration | `NETRCA_RUN_MININET_TESTS=1 ~/netrca-venv/bin/python -m pytest -q tests/test_monitoring_integration.py` | **2 passed** in 4.79 seconds, 1 existing dependency warning |
| Frontend component and integration tests | `npm test -- --run` | **9 files, 47 tests passed** |
| Frontend lint | `npm run lint` | **Passed** |
| Frontend route generation and typecheck | `npm run typecheck` | **Passed** |
| Frontend production build | `npm run build` | **Passed**; `/`, `/_not-found`, and `/icon.svg` generated |
| Mininet cleanup | OVS bridge, network namespace, and `mnexec` process inspection after the real test | **Clean** |
| Patch whitespace | `git diff --check` | **Passed** |

The 27 ordinary-suite skips are the repository's opt-in integration tests that
require explicit database, Mininet, or other external-test flags. The real
Mininet monitoring path was enabled separately and passed. The single warning
is the existing Starlette `TestClient` dependency deprecation warning.

## Demonstration workflow

1. Start the live Ubuntu backend and the real-data frontend using the Phase 3 instructions.
2. Open **Topology**, select **Start lab**, and confirm five devices and four links.
3. Open **Evidence** and select **Capture live snapshot**.
4. Point out the UTC-derived observation timestamp, `bytes_and_packets` counter semantics, interface states, and observed links.
5. Select two approved hosts and run **Run bounded probe**.
6. Explain packet counts, packet-loss percentage, and average latency as one measured path observation.
7. Distinguish this ephemeral runtime panel from the stored evidence tables below it.
8. Return to **Topology** and stop the lab.

## Limitations and stopping point

1. Capture is explicit and on-demand; this phase does not add background polling or streaming.
2. Interface byte and packet values are cumulative kernel counters, not calculated rates.
3. A probe is a short path observation, not historical availability or device health.
4. Live observations are not persisted by this panel; persistence remains an opt-in, database-backed pipeline with separate safeguards.
5. Mininet still requires the prepared Ubuntu WSL2 environment and elevated Linux privileges.
6. The installed Next.js version continues to report its known dependency-security advisory; remediation remains a separate reviewed change.

Stop after Phase 4. The next semester phase must be approved before controlled fault or analysis workflow changes begin.
