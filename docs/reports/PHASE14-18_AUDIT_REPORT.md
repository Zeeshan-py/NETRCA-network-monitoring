# NetRCA Phase 14–18 Audit and Corrections

## Scope and verdict

**Verdict: PARTIAL.** This audit reviewed the original Phase 14–18 prompts,
the corresponding reports, implementation, and tests. One confirmed frontend
defect was fixed: a failed RCA or impact read in incident detail was presented
as though no result existed. The dashboard now shows the sanitized API error
for the affected panel.

No migration, deployment, persistent seed, live Gemini request, live fault, or
unapproved schema change was made. The original `Instruction/` documents were
not changed.

## Requirement audit

| Phase | Requirement area | Status | Evidence and outcome |
| --- | --- | --- | --- |
| 14 | Local-only API and explicit write controls | PASS | All non-health routes use `_local_only`; state-changing routes also require `X-NetRCA-Local-Control: 1` and their default-off write flag. Forwarded client headers are rejected before loopback checks. See `backend/app/api/network.py` and the shared route helpers. |
| 14 | Input limits, safe errors, and browser protections | PASS | Pydantic bounds cover page sizes, probe/fault values, identifiers, and analysis inputs. `RequestBodyLimitMiddleware` applies a bounded streaming body check. The application returns sanitized error envelopes and adds no-store, nosniff, frame, and referrer headers. `backend/tests/test_security_hardening.py` passes. |
| 14 | Database security and integrity | PASS | Current rollback-only schema validation passed. The existing live catalog tests check RLS, client role restrictions, service-role scoping, and rollback behavior. SQL values are parameterized; dynamic table selection is allowlisted. No catalog, role, grant, or schema mutation was made in this audit. |
| 14 | Fault and Gemini safety | PASS | Fault operations remain local, header-protected, feature-gated, and bound to the owned lab topology. Gemini is backend-only, opt-in, and validates provider claims against server-authored evidence. No live provider or disruptive fault action was invoked. |
| 14 | Security verification completeness | PARTIAL | The frontend build now emits a Next.js known-vulnerability warning. The build succeeds after the required retry, but the dependency needs a deliberate security upgrade. No secret-scanning tool is configured, and current application logging has no authenticated actor or durable audit store; both remain documented limitations. |
| 15 | Evidence-to-explanation request path | PASS (test design) | `backend/tests/test_e2e_workflow_database_integration.py` uses the real API/service/store path, a deterministic provider selection stub, a shared rollback transaction, and post-rollback cleanup. It covers topology, collection, evidence, anomaly, correlation, RCA, impact, and explanation without a live Gemini call. |
| 15 | Current isolated-Mininet execution | PARTIAL | Ubuntu WSL2 has Mininet and OVS installed and active, but non-interactive sudo is unavailable. The root-only E2E Mininet test was not run in this audit; no lab was started. The Windows offline suite and WSL2 focused offline suite pass. |
| 15 | Failure, rollback, and security regression coverage | PASS | Offline tests cover malformed/duplicate evidence, unknown resources, inconclusive outcomes, provider failures, local-control failures, and sanitized errors. The database fixture suite validated rollback cleanup. |
| 16 | Real API-backed UI, pagination, stale-request handling, and local-control behavior | PASS | The dashboard/API client uses configured `NEXT_PUBLIC_API_BASE_URL`, validated envelope handling, abort signals, pagination, source separation, and explicit protected actions. Component and API-client tests pass. No browser credential is used. |
| 16 | Incident analysis error states | FIXED | RCA and impact retrieval failures were silently shown as an empty result. `dashboard.tsx` now retains and renders the sanitized error for each analysis panel. `page.test.tsx` verifies the impact-read error is visible. |
| 16 | Local demo documentation and safe controls | PASS | `README.md` documents loopback servers, guarded local-only seeding, explicit actions, disabled write flags, empty/error demonstrations, and shutdown. Fault controls are not exposed in the UI. |
| 17 | Read-only interactive topology graph | PASS | The SVG graph uses stable IDs, deterministic layout, zoom/pan/fit controls, selection, status handling, disconnected components, and partial-endpoint disclosure. It uses only existing read-only graph/context APIs. |
| 17 | Evidence and incident navigation | PASS | Stored device/link selections use only supported evidence filters. Incident topology context is retrieved explicitly and shows only backend-validated direct/one-hop stored references. Live and stored IDs are not mixed. |
| 17 | Populated real-browser verification | PARTIAL | Empty and error states are covered in component/API-client tests. A currently populated browser/API flow cannot be run safely because no disposable loopback PostgreSQL DSN is configured; the remote database is deliberately not seeded. |
| 18 | Empty-topology diagnosis | PASS | The stored topology path reads `public.devices` and `public.links`; an empty valid graph is handled by the frontend. The seed/report correctly classify the earlier result as missing demo data, not a graph-contract defect. |
| 18 | Safe repeatable fixture | PASS | `database/seed_local.py` rejects non-loopback DSNs. The fixture has stable IDs and conflict handling, includes a disconnected host plus linked evidence/RCA/impact records, and labels values as synthetic demo data. The database test suite validates it in a rollback-only transaction. |
| 18 | Populated end-to-end UI workflow | PARTIAL | The repository has a safe fixture and component coverage, but no local disposable database is configured for a real populated browser session. Static fixture records do not claim that Mininet, anomaly detection, deterministic analysis, or Gemini ran. |

## Defect corrected

`frontend/src/components/dashboard.tsx` previously ignored rejected
`getIncidentRca` and `getIncidentImpact` calls after an incident detail loaded.
The UI consequently stated that no result was available even for a database,
authorization, validation, or server failure. The fix stores each sanitized
failure separately and renders it in the matching analysis panel. It leaves a
true absent result as the existing empty-state message.

`frontend/src/app/page.test.tsx` now verifies that a rejected impact read is
presented as an alert, preventing regression.

## Tests run in this audit

| Environment | Command | Result |
| --- | --- | --- |
| Windows backend | `backend/.venv/Scripts/python.exe -m pytest -q` | **106 passed, 25 skipped**, one existing Starlette/httpx deprecation warning. |
| Windows database rollback suite | `NETRCA_RUN_DATABASE_TESTS=1 backend/.venv/Scripts/python.exe -m pytest ../database/tests -q` | **44 passed** in 69.88 seconds. Fixtures were inside a transaction that rolled back; no persistent demo data was created. |
| Ubuntu WSL2 focused offline suite | `/home/zeeshan/netrca-venv/bin/python -m pytest tests/test_security_hardening.py tests/test_pipeline.py tests/test_correlation.py tests/test_rca.py tests/test_impact.py tests/test_explanation.py -q` | **42 passed**, one existing deprecation warning. |
| Frontend | `npm test -- --run --reporter=dot` | **6 files, 31 tests passed**. |
| Frontend | `npm run lint` | Passed. |
| Frontend | `npm run typecheck` | Passed. |
| Frontend | `npm run build` | Compiled and completed after one required retry; it emits a known Next.js security-vulnerability warning. |

`git diff --check` passed before this report was added. The final tracked and
untracked report checks are recorded below.

## Skipped or unavailable verification

- The root-only WSL2 Mininet E2E test was not run: WSL2 is installed with
  Mininet/OVS available, but `sudo` requires interactive local authentication.
  No Mininet lab was started.
- No live Gemini request was made.
- No persistent local fixture or populated browser smoke was run: there is no
  explicitly configured loopback development database. The guarded seed runner
  refuses remote targets, and this audit did not seed the linked database.
- No dependency upgrade was made. The current Next.js build warning requires a
  separately reviewed security upgrade.
- No secret-scanner result is available because no scanner is configured.

## Final Git state

No commit, push, deployment, migration, or remote schema change was made.
The pre-existing `.gitignore` modification remains untouched. The generated
`frontend/AGENTS.md` file remains untracked. Audit changes are limited to the
incident-analysis error handling, its regression test, and this report.

Final whitespace verification: `git diff --check` passed, and the new untracked
audit report also passed `git diff --no-index --check`.
