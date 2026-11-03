# NetRCA Semester Completion Phase 10 — Evidence-Grounded Incident Explanation

**Date:** 2026-11-03

**Verdict:** PASS

**Schema migration:** none; explanations remain ephemeral by design

## Objective

Phase 10 turns the existing evidence-grounded Gemini endpoint into a dedicated,
reviewable operator workflow. An operator selects a stored incident with a
current deterministic RCA run, explicitly requests an explanation, and inspects
every backend-authored claim together with its evidence references.

```text
validated incident + current RCA + optional matching impact
                            │
                            ▼
        bounded server-authored EXPLANATION_INPUT_V1 claims
                            │
                            ▼
          Gemini returns claim-ID ordering only
                            │
                            ▼
       backend renders EXPLANATION_V1 with provenance
```

Gemini is an explanation organizer, not an RCA engine, impact engine, network
operator, recommendation authority, or remediation system.

## Implemented behavior

- Added a responsive **Explanation Lab** workspace and navigation entry.
- Lists stored incidents and loads selected incident, RCA, and optional impact
  context through the existing APIs.
- Requires a current deterministic RCA run before generation is enabled.
- Makes explanation generation an explicit operator action; incident loading
  and refresh never call Gemini automatically.
- Explains the trust boundary before generation: the backend authors claims,
  Gemini orders supplied IDs, and the backend renders accepted output.
- Displays summary, observed facts, candidate explanation, failure chain,
  impact, uncertainty, missing-evidence, and limitation sections separately.
- Keeps claim IDs visible and provides expandable typed evidence references.
- Displays model name and exact RCA/impact run identities.
- States that output is ephemeral and not persisted.
- Keeps deterministic RCA and impact visible and usable on provider failure.
- Adds actionable safe errors for missing/stale deterministic analysis.
- Updates the synthetic presentation fixture to the complete
  `EXPLANATION_V1` contract and explicitly labels it as no-Gemini output.

## Grounding and model boundary retained

The existing Phase 13 backend remains authoritative. It reads a consistent,
read-only snapshot, validates incident memberships and analysis fingerprints,
and constructs at most 80 bounded server-authored claims within the configured
input limit. Raw event/log messages, credentials, and unrelated incident data
are excluded.

The provider receives claim IDs as data with no tools. Its only accepted output
is a complete permutation of every supplied ID. Unknown, duplicate, missing,
malformed, or prose-bearing output is rejected. The public explanation is
rendered from the backend claim catalog, so the model cannot add measurements,
identifiers, causal claims, or remediation instructions.

## Access control and integrity

- `POST /api/v1/ai/incidents/{id}/explain` remains loopback-only.
- It requires `X-NetRCA-Local-Control: 1` and
  `NETRCA_GEMINI_ENABLED=true`.
- The Gemini key remains backend-only; it is never accepted from or rendered
  by the browser.
- Provider timeout, credential, rate-limit, malformed-output, and server errors
  return sanitized failures while deterministic findings remain available.
- Explanations are not written to `ai_analyses` or `recommendations`; the
  current schema lacks constrained exact RCA/impact provenance for persistence.
- No migration, remote seed, Mininet action, fault action, recommendation,
  remediation, or production-network operation is introduced by this phase.

## Files created

- `frontend/src/components/explanation-lab.tsx`
- `frontend/src/components/explanation-lab.test.tsx`
- `docs/reports/SEMESTER_PHASE10_EVIDENCE_EXPLANATION.md`

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
| Frontend component and integration tests | **15 files, 79 tests passed** |
| Frontend lint | **Passed** |
| Frontend route generation and TypeScript | **Passed** |
| Frontend production build | **Passed** after the required single security-advisory retry; all static routes generated |
| Focused explanation, RCA, and impact regression | **23 passed**, 1 existing dependency warning |
| Full Windows backend suite | **116 passed, 28 skipped**, 1 existing dependency warning |
| Full Ubuntu WSL2 backend suite | **116 passed, 28 skipped**, 1 existing dependency warning |
| Real Ubuntu Mininet/PostgreSQL end-to-end rollback | **1 passed** in 15.63 seconds, 1 existing dependency warning |

The end-to-end test exercised the real API/service/store path from Mininet
collection through persisted evidence, anomaly detection, correlation, RCA,
impact, and explanation. The explanation provider was replaced at its defined
selection boundary with a deterministic claim-ordering stub; no live Gemini
request or credential use occurred. PostgreSQL fixture rows were rolled back.
After shutdown, `ovs-vsctl list-br` returned no bridges and no Mininet or
`mnexec` process remained; the process query matched only its own shell.

The 28 default skips are opt-in database, Mininet, fault, E2E, and optional
dependency paths. The relevant E2E path was enabled separately. Provider
credentials, timeout, rate limit, malformed output, unknown/duplicate/missing
claim IDs, prompt-injection-shaped data, local access controls, and sanitized
failure behavior remain covered by the focused backend suite.

Next.js 16.4.0 reports a known security vulnerability and recommends a security
upgrade. The production build compiled and generated every route before the
advisory stopped the first command; the required single retry passed. A
dependency upgrade is intentionally separate from this phase.

## Demonstration workflow

1. Use an incident with a current stored RCA run and optional matching impact
   run.
2. Open **Explanation Lab** and select the incident.
3. Explain the backend-claim/model-ordering trust boundary.
4. Generate the explanation explicitly.
5. Review the separated factual, candidate, impact, uncertainty, and limitation
   sections.
6. Expand a claim and trace its stored evidence or deterministic-run reference.
7. Disable or disconnect the provider and show that deterministic RCA and
   impact remain available.

For the classroom presentation, use presentation mode and state that the result
is a static, evidence-linked browser fixture. It does not contact Gemini or
write to PostgreSQL.

## Limitations and stopping point

1. Explanation output is not persisted or retrievable after browser state is
   lost.
2. Live model behavior requires configured account access, network
   availability, and an enabled backend-only API key; it is not exercised by
   the safe test suite.
3. The model can organize only existing claims, which favors grounding over
   free-form prose.
4. Recommendations, incident reports, lifecycle updates, and remediation are
   intentionally outside Semester Phase 10.
5. Local-only control is suitable for the semester laboratory, not customer
   production authentication.

Stop after Semester Phase 10. Any next semester phase must be defined and
approved before implementation.
