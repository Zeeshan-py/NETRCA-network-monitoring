# NetRCA Semester Completion Phase 8 — Deterministic Root-Cause Investigation

**Date:** 2026-11-03

**Verdict:** PASS

**Schema migration:** none; the approved and verified `public.rca_runs` schema is reused

## Objective

Phase 8 turns the existing deterministic RCA service into a dedicated,
reviewable operator workflow. An operator chooses a stored incident, reviews its
correlated evidence, explicitly runs analysis, and inspects ranked candidates
with their exact rule contributions and source references.

```text
stored incident memberships + stored physical topology
                         │
                         ▼
         deterministic RULES_V1 candidate scoring
                         │
                         ▼
       CANDIDATES or honest INCONCLUSIVE result
                         │
                         ▼
  contributions + support + contradictions + limitations
```

The workflow exposes candidate hypotheses for human investigation. It does not
confirm causation, produce a calibrated probability, run impact analysis, call
Gemini, change incident status, or execute remediation.

## Implemented behavior

- Added a responsive **RCA Lab** workspace and navigation entry.
- Lists stored incidents from the existing paginated incident API.
- Loads the selected incident's original events, anomalies, and latest RCA run.
- Runs analysis only after an explicit operator action for the selected incident.
- Displays candidate rank, cause type, stable target identity, explanation, and
  uncalibrated integer rule score.
- Displays each rule contribution and its point value.
- Preserves original supporting and contradictory evidence identifiers,
  timestamps, metric references, and reason codes.
- Displays candidate-level and run-level limitations.
- Presents `INCONCLUSIVE` as an intentional outcome and never invents a cause.
- Links the investigation to the existing stored-topology evidence context.
- Labels presentation mode as a static browser replay with no database or model
  call.

## Deterministic boundary retained

The existing Phase 11 engine remains authoritative. Direct stored failure or
state-down evidence seeds a candidate. Independent direct observations and
later related symptoms can add bounded points. Contradictions such as symptoms
preceding a failure or a resolved failure subtract points. Graph-cut evidence
can support an already seeded candidate but cannot establish causation alone.
A supported candidate requires the existing deterministic threshold; otherwise
the result remains `INCONCLUSIVE`.

Scores are `UNCALIBRATED_RULE_POINTS`. They are neither percentages nor
confidence probabilities. The UI states this beside every candidate.

## Access control and integrity

- `GET /api/v1/incidents/{id}/root-causes` remains local-only and read-only.
- `POST /api/v1/incidents/{id}/root-cause/analyze` requires loopback access,
  `X-NetRCA-Local-Control: 1`, and `NETRCA_RCA_WRITES_ENABLED=true`.
- The request carries no caller-authored evidence or score. The backend reads
  the incident's validated stored memberships.
- The existing transaction lock, fingerprint, idempotent run reuse, and
  evidence limits remain unchanged.
- Database errors remain sanitized. No credential is rendered or logged.
- No migration, remote seed, Mininet action, fault action, Gemini request, or
  production-network operation is introduced by this phase.

## Files created

- `frontend/src/components/rca-lab.tsx`
- `frontend/src/components/rca-lab.test.tsx`
- `docs/reports/SEMESTER_PHASE8_RCA_INVESTIGATION.md`

## Files updated

- `frontend/src/lib/api.ts`
- `frontend/src/lib/api.test.ts`
- `frontend/src/components/dashboard.tsx`
- `frontend/src/app/page.test.tsx`
- `frontend/src/app/globals.css`
- `docs/presentations/PRESENTATION_RUNBOOK.md`
- `docs/reports/INDEX.md`
- `README.md`

## Verification

| Check | Actual result |
|---|---|
| Frontend component and integration tests | **13 files, 68 tests passed** |
| Frontend lint | **Passed** |
| Frontend route generation and TypeScript | **Passed** |
| Frontend production build | **Passed** after the required single security-advisory retry; all static routes generated |
| Focused RCA, correlation, and graph regression | **23 passed**, 1 existing dependency warning |
| Full Windows backend suite | **116 passed, 28 skipped**, 1 existing dependency warning |
| Full Ubuntu WSL2 backend suite | **116 passed, 28 skipped**, 1 existing dependency warning |
| Windows real PostgreSQL RCA rollback suite | **4 passed** in 13.35 seconds |
| Ubuntu real PostgreSQL RCA rollback suite | **4 passed** in 9.24 seconds |

The 28 default skips are opt-in database, Mininet, fault, E2E, and optional
dependency paths. The dedicated RCA database suites were enabled explicitly on
both Windows and Ubuntu. They exercise real persistence, candidate and
inconclusive runs, idempotency, provenance, constraint rollback, and advisory
lock contention; their test rows are rolled back. Mininet was not required or
started, so no virtual-network cleanup was necessary. No live Gemini request
was made.

Next.js 16.4.0 reports a known security vulnerability and recommends a security
upgrade. The production build compiled and generated every route before the
advisory stopped the first command; the required single retry passed. A
dependency upgrade is intentionally separate from this phase.

## Demonstration workflow

1. Start the backend with PostgreSQL configured and
   `NETRCA_RCA_WRITES_ENABLED=true`.
2. Ensure a correlated stored incident exists from Semester Phase 7.
3. Open **RCA Lab** and choose that incident.
4. Review its event/anomaly counts and stored topology context.
5. Run deterministic RCA explicitly.
6. Explain the candidate rank, integer rule contributions, supporting and
   contradictory evidence, and limitations.
7. If the result is `INCONCLUSIVE`, explain that NetRCA preserves uncertainty
   instead of fabricating a root cause.

For a database-independent classroom presentation, enable presentation mode and
state that the populated result is a static browser fixture with no remote
write.

## Limitations and stopping point

1. The engine analyzes stored incident membership and current stored topology;
   it does not have a historical topology snapshot bound to the incident.
2. A candidate is evidence-supported but not independently proven causal.
3. Incident status transitions and response coordination remain outside this
   phase.
4. Impact analysis, Gemini explanation, recommendations, and remediation are
   intentionally not part of Semester Phase 8.
5. Local-only controls are appropriate for the semester laboratory, not
   customer production authentication.

Stop after Semester Phase 8. A later approved semester phase may expose the
existing deterministic impact and failure-chain analysis.
