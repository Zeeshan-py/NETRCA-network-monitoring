# NetRCA Semester Completion Phase 7 — Evidence Correlation and Incident Grouping

**Date:** 2026-11-03

**Verdict:** PASS

**Schema migration:** none; the previously approved Phase 9 incident-anomaly schema is reused

## Objective and result

Phase 7 exposes the existing deterministic correlation engine as a deliberate,
reviewable dashboard workflow. An operator selects validated stored events and
anomalies, submits only those identifiers, inspects whether an incident was
created or reused, reviews every stored relationship reason, and can open the
resulting incident with its original evidence.

```text
selected Phase 6 events + selected Phase 8 anomalies
                         │
                         ▼
       bounded time + explicit direct relationship
                         │
                         ▼
              DETECTED incident or safe reuse
                         │
                         ▼
             membership reason + original evidence
```

Correlation remains grouping, not causation. This phase does not run graph
analysis, RCA, impact analysis, Gemini, remediation, or incident closure.

## Implemented behavior

- Added a responsive **Correlation Lab** workspace.
- Replaced the broad “correlate current page” shortcut with explicit evidence
  selection.
- Limits each request to 100 combined event and anomaly identifiers.
- Shows the authoritative relationship rules before an operator writes.
- Displays created, attached, and skipped counts.
- Distinguishes newly created incidents from reused open incidents.
- Displays each membership's evidence kind, stable identifier, and grounded
  reason such as `SEED`, `SAME_DEVICE`, `SAME_LINK`, `LINK_ENDPOINT`,
  `SOURCE_EVENT`, `SOURCE_METRIC`, or `EXISTING`.
- Opens the resulting incident through the existing incident detail workflow.
- Keeps unrelated, stale, invalid, closed, or ambiguously assigned evidence
  visibly separate or skipped.
- In presentation mode, the same interface is explicitly labeled as a synthetic
  browser replay and performs no remote write.

## Correlation and lifecycle rules retained

- Time proximity is required but never sufficient.
- Direct shared device, link, service, source event, source metric, or known
  link endpoint relationships are allowed.
- Different explicit services and unsupported topology relationships do not
  group.
- No multi-hop dependency inference or name-based guess is performed.
- New incidents begin as `DETECTED`.
- Related evidence may reuse only a `DETECTED` or `INVESTIGATING` incident.
- Existing resolved or closed incidents are not reopened.
- Severity is the highest valid severity among existing and newly attached
  evidence.
- Repeated runs are idempotent, and ambiguous multi-incident membership is
  rejected rather than merged silently.
- PostgreSQL transaction and advisory-lock behavior remains authoritative.

## Safety and integrity

- Real correlation requires `NETRCA_CORRELATION_WRITES_ENABLED=true`, a
  loopback caller, and `X-NetRCA-Local-Control: 1`.
- Only identifiers returned by stored evidence APIs are selectable.
- Evidence rows are not rewritten or fabricated.
- Root cause, confidence, impact, AI, and remediation fields are untouched.
- No migration, seed, retained test row, Mininet operation, Gemini request,
  Docker operation, external scan, or production-network action occurred.

## Files created

- `frontend/src/components/correlation-lab.tsx`
- `frontend/src/components/correlation-lab.test.tsx`
- `docs/reports/SEMESTER_PHASE7_CORRELATION_INCIDENTS.md`

## Files updated

- `frontend/src/lib/api.ts`
- `frontend/src/lib/api.test.ts`
- `frontend/src/components/dashboard.tsx`
- `frontend/src/app/page.test.tsx`
- `frontend/src/app/globals.css`
- `docs/guides/event-correlation.md`
- `docs/presentations/PRESENTATION_RUNBOOK.md`
- `docs/reports/INDEX.md`
- `README.md`

## Verification

| Check | Actual result |
|---|---|
| Focused correlation, pipeline, and anomaly regression | **23 passed, 1 skipped**, 1 existing dependency warning |
| Real PostgreSQL correlation rollback suite | **3 passed** in 10.39 seconds |
| Frontend component and integration tests | **12 files, 62 tests passed** |
| Frontend lint | **Passed** |
| Frontend route generation and typecheck | **Passed** |
| Full Windows backend suite | **116 passed, 28 skipped**, 1 existing dependency warning |
| Full Ubuntu backend suite | **116 passed, 28 skipped**, 1 existing dependency warning |
| Frontend production build | **Passed** after the required single advisory retry; all static routes generated |
| `git diff --check` | **Passed** |

The focused skip is the optional real scikit-learn fixture. The PostgreSQL
suite exercised actual transactions, incident creation and reuse, membership
idempotency, severity and separation, foreign-key rollback, and transaction
advisory-lock exclusion. Its inserted topology, evidence, anomaly, incident,
and membership rows were rolled back.

Next.js 16.4.0 reports a known security vulnerability and recommends a security
upgrade. The production build passed after the tool's required single retry; no
dependency upgrade was included in this phase.

## Demonstration workflow

For a real stored-evidence demonstration:

1. Start the local backend with the database configured and
   `NETRCA_CORRELATION_WRITES_ENABLED=true`.
2. Ensure validated events or persisted positive anomalies exist from earlier
   phases.
3. Open **Correlation Lab** and select only evidence intended for the run.
4. Explain the direct relationship rules and run correlation.
5. Review created/reused state, attachment count, skipped evidence, and each
   relationship reason.
6. Open the resulting incident and inspect its original evidence.

For a database-independent presentation, use presentation mode and identify the
operation as a synthetic browser replay with no remote write.

## Limitations and stopping point

1. Correlation operates on explicitly selected current-page evidence; there is
   no background scan or automatic incident declaration.
2. It does not establish a root cause or business impact.
3. Service-only correlation depends on validated stored service evidence, which
   the current Mininet collector does not generate.
4. The local control boundary is suitable for the semester lab, not production
   customer authentication.
5. Incident status transitions remain outside this workflow.

Stop after Phase 7. The next approved semester phase may expose deterministic,
evidence-backed RCA candidates for an incident.
