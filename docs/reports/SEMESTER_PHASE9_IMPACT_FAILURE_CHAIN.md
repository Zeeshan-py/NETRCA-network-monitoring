# NetRCA Semester Completion Phase 9 — Impact and Failure-Chain Analysis

**Date:** 2026-11-03

**Verdict:** PASS

**Schema migration:** none; the approved and verified `public.impact_runs` schema is reused

## Objective

Phase 9 exposes the existing deterministic impact engine as a dedicated,
reviewable workflow. An operator chooses a stored incident with an RCA run,
explicitly runs analysis, and inspects directly observed components separately
from conservative structural exposure.

```text
latest validated RCA + incident evidence + stored topology
                            │
                            ▼
             deterministic IMPACT_RULES_V1
                            │
                            ▼
          ASSESSED or honest INCONCLUSIVE result
                            │
                            ▼
 observed components + potential one-hop chain + limitations
```

The workflow does not confirm that the leading RCA candidate caused an outage,
infer traffic direction, calculate customer impact, or execute remediation.

## Implemented behavior

- Added a responsive **Impact Lab** workspace and navigation entry.
- Lists stored incidents and loads the selected incident, latest RCA run, and
  latest impact run through the existing APIs.
- Requires a stored RCA run before impact analysis can be requested.
- Runs analysis only after an explicit operator action for the selected incident.
- Displays affected device, link, and service counts without hiding each
  entity's evidence classification.
- Separates `OBSERVED` components backed by direct validated incident evidence
  from `POTENTIAL` one-hop topology or hosting exposure.
- Displays ordered structural-chain edges, supported relationship type,
  explanation, and original evidence references.
- States that chain step order is structural, not measured chronology.
- Keeps user/application impact `UNKNOWN_UNVERIFIED`.
- Displays run limitations and preserves empty `INCONCLUSIVE` outcomes.
- Links back to the dedicated RCA view and stored topology context.
- Keeps presentation mode as a labeled static browser replay with no database,
  Mininet, or model call.

## Deterministic boundary retained

The existing Phase 12 engine remains authoritative. A uniquely leading,
currently validated RCA candidate must map to the stored topology. The directly
evidenced failed component is `OBSERVED`. Verified physical endpoints,
one-hop adjacency, and active device-service mappings may be `POTENTIAL`.
Analysis never walks a second physical hop or invents directed dependencies.
Additional directly evidenced failures can be reported without fabricating a
chain to the leading candidate.

An inconclusive RCA, tied leading candidates, stale RCA input, missing direct
evidence, unmappable target, or invalid topology produces an `INCONCLUSIVE`
impact result rather than affected entities or severity guesses.

## Access control and integrity

- `GET /api/v1/incidents/{id}/impact` and `/failure-chain` remain local-only.
- `POST /api/v1/incidents/{id}/impact/analyze` requires loopback access,
  `X-NetRCA-Local-Control: 1`, and `NETRCA_IMPACT_WRITES_ENABLED=true`.
- The browser submits only the selected incident identifier. The backend reads
  the current stored RCA, memberships, topology, and service mappings.
- Existing transaction locks, fingerprints, idempotent reuse, stale-input
  rejection, and evidence limits remain unchanged.
- No incident, RCA, confirmed impact, recommendation, AI, or network-control
  record is rewritten.
- No migration, remote seed, Mininet action, fault action, Gemini request, or
  production-network operation is introduced by this phase.

## Files created

- `frontend/src/components/impact-lab.tsx`
- `frontend/src/components/impact-lab.test.tsx`
- `docs/reports/SEMESTER_PHASE9_IMPACT_FAILURE_CHAIN.md`

## Files updated

- `frontend/src/lib/api.ts`
- `frontend/src/lib/api.test.ts`
- `frontend/src/lib/presentation-demo.ts`
- `frontend/src/lib/presentation-demo.test.ts`
- `frontend/src/components/dashboard.tsx`
- `frontend/src/app/page.test.tsx`
- `frontend/src/app/globals.css`
- `docs/presentations/PRESENTATION_RUNBOOK.md`
- `docs/reports/INDEX.md`
- `README.md`

## Verification

| Check | Actual result |
|---|---|
| Frontend component and integration tests | **14 files, 74 tests passed** |
| Frontend lint | **Passed** |
| Frontend route generation and TypeScript | **Passed** |
| Frontend production build | **Passed** after the required single security-advisory retry; all static routes generated |
| Focused impact, RCA, and graph regression | **20 passed**, 1 existing dependency warning |
| Full Windows backend suite | **116 passed, 28 skipped**, 1 existing dependency warning |
| Full Ubuntu WSL2 backend suite | **116 passed, 28 skipped**, 1 existing dependency warning |
| Windows real PostgreSQL impact rollback suite | **3 passed** in 18.03 seconds |
| Ubuntu real PostgreSQL impact rollback suite | **3 passed** in 9.79 seconds |

The 28 default skips are opt-in database, Mininet, fault, E2E, and optional
dependency paths. The dedicated impact database suites were enabled explicitly
on both Windows and Ubuntu. They exercise real assessed and inconclusive run
persistence, repeated-run idempotency, stale topology rejection, constraint
rollback, and cleanup; their fixture rows are rolled back. Mininet was not
required or started, so no virtual-network cleanup was necessary. No live
Gemini request was made.

Next.js 16.4.0 reports a known security vulnerability and recommends a security
upgrade. The production build compiled and generated every route before the
advisory stopped the first command; the required single retry passed. A
dependency upgrade is intentionally separate from this phase.

## Demonstration workflow

1. Start the backend with PostgreSQL configured and
   `NETRCA_IMPACT_WRITES_ENABLED=true`.
2. Use an incident with a current stored RCA run from Semester Phase 8.
3. Open **Impact Lab** and choose the incident.
4. Review the RCA prerequisite and run impact analysis explicitly.
5. Contrast `OBSERVED` evidence with `POTENTIAL` structural exposure.
6. Follow the bounded chain and inspect its evidence references.
7. Explain that `UNKNOWN_UNVERIFIED` means no defensible customer or
   application-impact claim is available.
8. If the result is `INCONCLUSIVE`, show that no affected entity was invented.

For a database-independent classroom presentation, enable presentation mode and
identify the populated result as a static browser fixture with no remote write.

## Limitations and stopping point

1. Stored topology is current state, not a historical snapshot bound to the
   incident timestamp.
2. Physical topology is undirected; chain order is structural exposure, not
   measured propagation direction or chronology.
3. Potential services are mapped exposures, not confirmed service outages.
4. No incident-scoped user/application observation supports a customer-impact
   count, duration, or severity.
5. Gemini explanation, recommendations, incident lifecycle updates, and
   remediation remain outside Semester Phase 9.
6. Local-only controls are appropriate for the semester laboratory, not
   customer production authentication.

Stop after Semester Phase 9. A later approved semester phase may add the
existing evidence-grounded explanation workflow without changing deterministic
RCA or impact findings.
