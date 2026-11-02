# NetRCA Semester Completion Phase 5 — Controlled Fault and Observable Failure

**Date:** 2026-11-02

**Verdict:** PASS WITH DOCUMENTED LIMITATIONS

**Schema migration:** none

## Objective and result

Phase 5 connects the existing bounded Mininet fault service to a dedicated
operator workflow. A local operator can select only validated live interfaces
or links, inject one time-bounded fault, observe its lifecycle, capture the
resulting network state, and explicitly recover or reset the fault.

```text
validated live snapshot ──► fixed fault selector ──► local-control API
                                                      │
                                                      ▼
                                              owned Mininet lab
                                                      │
                         observed counters/state ◄────┘
```

This phase demonstrates causally controlled lab input and observable output. It
does not claim that the injected fault is itself an anomaly, incident, or root
cause finding. Those conclusions require separately stored evidence and
deterministic analysis.

## Implemented behavior

- Added a responsive **Fault Lab** workspace to the dashboard.
- Loads the four supported backend fault types rather than presenting
  unimplemented instruction-document examples.
- Derives interface and link choices only from the current canonical live
  monitoring snapshot.
- Limits packet-loss and latency shaping targets to HOST and SERVER ports.
- Offers fixed, bounded parameters: 15/30/60 seconds, 25/50/100 percent packet
  loss, and 25/50/100 milliseconds latency.
- Displays the active fault, expiry time, severity, in-process lifecycle,
  restoration result, and honest persistence status.
- Blocks a second injection while one fault is active.
- Provides explicit recovery, controller reset, safe-target refresh, and
  post-fault evidence capture actions.
- Keeps all mutation controls unavailable in browser-only presentation mode.
- Added actionable frontend handling for disabled controls, active-fault
  conflicts, and missing in-process records.

## Safety and integrity

- Every mutation remains loopback-only and requires
  `X-NetRCA-Local-Control: 1`.
- `NETRCA_FAULT_INJECTION_ENABLED` remains disabled by default.
- No free-form command, IP address, interface, node, link, percentage, latency,
  or duration is accepted by the dashboard.
- The backend remains authoritative for topology ownership, target validation,
  one-active-fault serialization, captured pre-state, expiry, and restoration.
- Fault application does not fabricate evidence or write an anomaly, incident,
  RCA, or impact result.
- No schema migration, remote database write, Supabase seed, Gemini request,
  Docker operation, external scan, or production-network action was performed.

## Files created

- `frontend/src/components/fault-lab.tsx`
- `frontend/src/components/fault-lab.test.tsx`
- `docs/reports/SEMESTER_PHASE5_CONTROLLED_FAULT.md`

## Files updated

- `frontend/src/lib/api.ts`
- `frontend/src/lib/api.test.ts`
- `frontend/src/components/dashboard.tsx`
- `frontend/src/app/page.test.tsx`
- `frontend/src/app/globals.css`
- `backend/tests/test_faults_mininet_integration.py`
- `docs/guides/fault-injection.md`
- `docs/presentations/PRESENTATION_RUNBOOK.md`
- `docs/reports/INDEX.md`
- `README.md`

## Verification

| Check | Result |
|---|---|
| Focused Windows fault and monitoring regression | **17 passed, 4 skipped**, 1 existing dependency warning |
| Real Ubuntu Mininet fault and monitoring API suite | **4 passed** in 7.57 seconds, 1 existing dependency warning |
| Frontend component and integration tests | **10 files, 52 tests passed** |
| Frontend lint | **Passed** |
| Frontend route generation and typecheck | **Passed** |
| Full Windows backend suite | **116 passed, 28 skipped**, 1 existing dependency warning |
| Full Ubuntu backend suite | **116 passed, 28 skipped**, 1 existing dependency warning |
| Frontend production build | **Passed** after the required single advisory retry; all static routes generated |
| Mininet cleanup | **Clean**: no OVS bridges, network namespaces, or `mnexec` processes |
| `git diff --check` | **Passed** |

Default-suite skips remain explicit opt-in PostgreSQL, Mininet, E2E, and
optional dependency cases. The real Mininet tests relevant to this phase are
enabled separately.

Next.js 16.4.0 reports a known security vulnerability and recommends a security
upgrade. The build passed after the tool's required single retry. No dependency
upgrade was performed because it is a separate, potentially broad change that
requires review.

## Demonstration workflow

1. Start the Ubuntu WSL2 backend with simulation and fault injection enabled.
2. Start the frontend in real-data mode.
3. Open **Topology**, start the canonical five-node lab, and verify connectivity.
4. Open **Fault Lab** and refresh the validated targets.
5. Select **Interface failure**, target `h1 · h1-eth0`, and inject a 30-second
   fault.
6. Select **Capture post-fault evidence** and show the down interface and link.
7. Return to **Fault Lab**, recover the active fault, and refresh the evidence to
   show restoration.
8. Return to **Topology** and stop the lab before closing the backend.

## Limitations and stopping point

1. Fault history is process-local unless an exact stored topology mapping and
   reachable database allow best-effort persistence.
2. Abrupt backend termination can interrupt scheduled restoration; the owned
   lab must be stopped before the demonstration ends.
3. Only the four existing safely restorable fault types are exposed. The wider
   fault list in the original vision remains future scope.
4. This phase does not automatically persist observations or run anomaly,
   correlation, RCA, impact, or AI explanation workflows.
5. Mininet and Open vSwitch require the prepared Ubuntu WSL2 environment and
   elevated Linux privileges.

Stop after Phase 5. A later semester phase may connect explicitly stored fault
observations to deterministic analysis after separate approval.
