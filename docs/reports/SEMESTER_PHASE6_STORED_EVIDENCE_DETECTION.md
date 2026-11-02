# NetRCA Semester Completion Phase 6 — Stored Evidence and Deterministic Anomaly Detection

**Date:** 2026-11-02

**Verdict:** PASS LOCALLY; REAL DATABASE VERIFICATION BLOCKED

**Schema migration:** none

## Objective and result

Phase 6 adds an explicit dashboard workflow over the existing Phase 6 evidence
pipeline and Phase 8 anomaly service. An operator can request persistence of a
validated live snapshot or bounded probe, refresh stored evidence, select up to
20 supported stored metrics, and run deterministic anomaly detection without
persisting the returned findings.

```text
owned Mininet lab ──► explicit collection ──► PostgreSQL metrics
                                                  │
                                     selected stored metric IDs
                                                  │
                                                  ▼
                                  deterministic anomaly detector
                                  threshold / baseline / optional IF
```

No automatic collection, polling, correlation, incident creation, RCA, impact
analysis, or Gemini request is introduced.

## Implemented behavior

- Added a responsive **Detection Lab** dashboard workspace.
- Added explicit **Store current snapshot** and **Store bounded probe** actions.
- Probe endpoints are restricted to HOST and SERVER names from the current
  validated monitoring snapshot; packet count and timeout remain fixed.
- Displays honest collection counts for metrics, events, duplicates, unmapped
  links, observation time, and probe state.
- Filters the current stored metric page to the detector's supported evidence:
  latency, packet loss, availability, interface/link state, and error counters.
- Excludes cumulative traffic counters because one observation cannot establish
  a rate.
- Limits a detection request to 20 selected stored metric IDs.
- Sends `persist: false` for detection, so findings remain review results and do
  not create anomaly rows.
- Displays status, method, reason, severity, method-specific score, score kind,
  baseline sample count, and persistence status.
- Explicitly labels scores as strength values rather than probabilities.
- Keeps all collection and detection controls unavailable in synthetic
  presentation mode.

## Safety and integrity

- Pipeline writes remain disabled unless
  `NETRCA_PIPELINE_WRITES_ENABLED=true` is explicitly set on the local backend.
- Every POST remains loopback-only and requires
  `X-NetRCA-Local-Control: 1`.
- The dashboard does not submit arbitrary resource IDs for collection, manual
  observations, topology records, commands, addresses, or database values.
- Stored metric IDs originate from the existing paginated evidence API.
- Anomaly persistence remains off in this semester workflow.
- No migration, database seed, retained test row, Gemini request, Docker
  operation, external scan, or production-network action was performed.

## Files created

- `frontend/src/components/detection-lab.tsx`
- `frontend/src/components/detection-lab.test.tsx`
- `docs/reports/SEMESTER_PHASE6_STORED_EVIDENCE_DETECTION.md`

## Files updated

- `frontend/src/lib/api.ts`
- `frontend/src/lib/api.test.ts`
- `frontend/src/components/dashboard.tsx`
- `frontend/src/app/page.test.tsx`
- `frontend/src/app/globals.css`
- `docs/guides/evidence-pipeline.md`
- `docs/guides/anomaly-detection.md`
- `docs/presentations/PRESENTATION_RUNBOOK.md`
- `docs/reports/INDEX.md`
- `README.md`

## Verification

| Check | Actual result |
|---|---|
| Focused backend pipeline and anomaly tests | **14 passed, 1 skipped**, 1 existing dependency warning |
| Frontend component and integration tests | **11 files, 57 tests passed** |
| Frontend lint | **Passed** |
| Frontend route generation and typecheck | **Passed** |
| PostgreSQL pipeline and anomaly rollback tests | **2 failed before transactions** because the configured pooler could not be reached |
| Real Mininet-to-PostgreSQL rollback test | Mininet snapshot and probe succeeded; the test then **failed before a database transaction** because the pooler hostname could not be resolved |
| Full Windows backend suite | **116 passed, 28 skipped**, 1 existing dependency warning |
| Full Ubuntu backend suite | **116 passed, 28 skipped**, 1 existing dependency warning |
| Frontend production build | **Passed**; `/`, `/_not-found`, and `/icon.svg` generated |
| Mininet cleanup | **Clean**: no OVS bridges, network namespaces, or `mnexec` processes |
| `git diff --check` | **Passed** |

The one focused skip is the optional real scikit-learn fixture. Deterministic
threshold, robust-baseline, counter, validation, API-control, and persistence
orchestration paths ran through unit tests. Database persistence is not claimed
as verified in this run. No connection retry or alternate database target was
attempted after the diagnosed endpoint failures.

## Demonstration workflow

When the configured database is reachable and contains the active canonical
topology mapping:

1. Start the Ubuntu backend with simulation, fault injection, pipeline writes,
   and local CORS explicitly enabled.
2. Start the frontend in real-data mode and start the Mininet lab.
3. Optionally inject a controlled fault in **Fault Lab**.
4. Open **Detection Lab** and store a snapshot or bounded probe.
5. Refresh stored evidence and select supported metrics from the current page.
6. Run detection and explain the method, reason, severity, score semantics, and
   evidence source.
7. Recover any active fault and stop the lab.

If PostgreSQL remains unreachable, demonstrate Phase 6 through its tested UI
and explain the database-unavailable error honestly; do not fabricate stored
metrics or claim persistence.

## Limitations and stopping point

1. The configured PostgreSQL pooler was unreachable during this phase, so real
   persistence and stored-history detection were not re-verified.
2. Collection remains on demand and requires canonical live names to map to
   active stored topology rows.
3. Detection operates on the current metric page and does not schedule or poll.
4. Isolation Forest remains optional and requires sufficient varied historical
   samples plus the installed dependency.
5. This phase intentionally stops before correlation, incident grouping, RCA,
   impact analysis, or AI explanation workflow changes.

Stop after Phase 6 and wait for approval before beginning the next semester
analysis phase.
