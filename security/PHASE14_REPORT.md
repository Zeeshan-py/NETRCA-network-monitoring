# Phase 14 — Security Hardening and Access-Control Verification

**Status:** implemented and verified locally; not committed or pushed
**Branch:** `main`
**Database migration:** none required or applied

## Findings and changes

| Severity | Finding | Action and current status |
| --- | --- | --- |
| High (deployment risk) | The application has no user authentication or per-user authorization. The loopback check and fixed `X-NetRCA-Local-Control: 1` value are local-development controls, not authentication. | Preserved the documented single-user loopback model and confirmed control writes remain opt-in behind feature flags. Do not expose this API to a LAN, proxy, or the public internet without real authentication and authorization. |
| Medium | Backend transactions used a configured Supabase login with role-creation, database-creation, and RLS-bypass attributes. | Every application transaction now switches locally to the existing `service_role`. A live query confirmed the effective role cannot create roles, databases, or public-schema objects; table-scoped CRUD remains available. Read-only incident explanation loads use a repeatable-read, read-only transaction. |
| Medium | Forwarded headers could be misread by a future deployment or proxy setup as trustworthy client identity. | Local API routes reject `Forwarded`, `X-Forwarded-*`, and `X-Real-IP` headers. The README development command disables Uvicorn proxy-header interpretation. |
| Medium | Requests had no application-wide body-size cap, and responses lacked consistent cache and browser security headers. | Added a streaming ASGI body cap (default 256 KiB, configurable from 64 KiB to 1 MiB) that returns sanitized HTTP 413, plus `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: no-referrer`. CORS still wraps body-limit responses. |
| Low | The live database contains a `SECURITY DEFINER` function named `public.rls_auto_enable()` with client-role execute ACLs. | Read-only inspection confirmed it is attached as a PostgreSQL event trigger, not an ordinary callable function; direct execution under `anon` was rejected. Client roles have no `CREATE` on `public`. No database change was made. |
| Medium (accepted gap) | Security-relevant requests are logged with method, path, status, and duration, but there is no authenticated actor identity or durable audit subsystem. | Confirmed current sanitized request logging. No audit schema or subsystem was introduced. Existing records and application logs do not establish who initiated an operation. |

The live target was the configured Supabase project `oeizpptglvtnljkheatq` (PostgreSQL 17.11). No credentials or connection strings are included here. All 20 operational tables checked have RLS enabled; `anon` and `authenticated` lack table CRUD, while `service_role` has the expected table CRUD. Neither client role can create objects in `public`. Existing foreign keys and constraints were left unchanged. No remote schema or data was modified.

## Route access review

All application routes were inspected in their actual router and dependency paths. `GET /api/v1/health` is the sole intentionally public endpoint and returns only API health. Other reads require a direct loopback peer and, where an Origin is supplied, an allowed configured origin. State-changing local-control operations additionally require the exact `X-NetRCA-Local-Control: 1` header and the relevant default-off feature flag.

| Route group | Access and validation verified | Sensitive response / tests |
| --- | --- | --- |
| Network status, topology, start/stop/restart/reset, connectivity test | Local-only; control header for operations; simulation/manager availability gates; no caller-provided shell command or arbitrary target. | Local topology and status. Existing network unit/API tests; new forwarded-header and invalid-control tests. |
| Monitoring snapshot and probe | Local-only; probe is control-protected and limited to 1–3 probes with 1–2 second timeout. | Local metrics and probe results. Existing monitoring tests. |
| Metrics, logs, events, collection, pipeline probe | Local-only; writes require control header and `pipeline_writes_enabled`; batches capped at 100 and fields bounded; probe bounds match monitoring. | Stored operational evidence. Existing Phase 6 tests and opt-in PostgreSQL rollback tests. |
| Fault inject, recover, cancel, reset | Local-only; control header and default-off `fault_injection_enabled`; fixed topology target/interface allowlist, shell-free command arguments, one active fault, duration <=300 seconds, loss <=100%, latency <=250 ms, tracked restoration. | Fault records and state. Existing mocked fault tests; real Mininet/network changes were not run. |
| Anomaly detection and stored results | Local-only; control header; persistence requires its opt-in flag; input is bounded to 20 evidence items. | Stored anomalies and evidence. Existing Phase 8 tests. |
| Event correlation; incident list/detail | Correlation trigger is local-only, control-protected, and feature-flagged; input IDs capped at 100. Listing/detail are local-only and paginated. | Incidents and source evidence. Existing Phase 9 API and PostgreSQL rollback tests. |
| RCA analysis and run retrieval | Trigger is local-only, control-protected, and feature-flagged; bounded evidence input (100 events and 100 anomalies). | RCA results and referenced evidence. Existing Phase 11 tests. |
| Impact analysis and run retrieval | Trigger is local-only, control-protected, and feature-flagged. | Potential/confirmed impact records and evidence. Existing Phase 12 tests. |
| Gemini incident explanation | Trigger is local-only, control-protected, and feature-flagged; credential required server-side; input <=12 KiB and 80 claims; timeout 2–30 seconds; candidate claims and evidence IDs validated. | Validated explanation only. Existing Phase 13 tests cover evidence reference/output validation. No live provider call was made. |

The direct-peer policy accepts loopback IP representations, including IPv4-mapped IPv6 loopback, and does not derive identity from proxy headers. Unknown/malformed remote peer values are rejected. Error responses for database/provider failures use sanitized messages. Database values are parameterized; the only dynamic table identifier in the pipeline is selected from a static allowlist.

## Input, secrets, and fault-safety review

Pydantic route models and parameters were checked for identifier parsing, enum validation, numeric bounds, pagination limits, evidence references, and expensive-operation limits. The new body-size limit applies before route parsing and does not trust `Content-Length`; it counts received bytes. Its implementation buffers at most the configured cap per request before replaying the body to FastAPI.

Tracked environment templates contain variable names and blank secret values only. Real backend/frontend environment files are ignored by Git; their values were not printed. No frontend reference to the Gemini credential was found; Gemini credentials are read by backend settings/provider code. Existing dependency lock information is available for the frontend, but no Python lockfile or Python dependency audit tool is present. Secret-scanning executables (`gitleaks`, `trufflehog`, and `detect-secrets`) were not installed, so no scanner result is claimed. The frontend was not changed and no frontend build was needed.

Fault controls remain disabled by default and target only the owned local lab topology. Tests used mocks and database rollback fixtures; no real Mininet test, external network fault, or live Gemini call ran. Recovery/restoration failure paths remain represented by existing fault controller status and retry handling; this phase did not change those lifecycle semantics.

## Verification

Windows offline suite, from `backend/`:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Result: **104 passed, 24 skipped**, with one Starlette/httpx deprecation warning. Skips include opt-in database/lab integration tests and the optional scikit-learn-dependent test when its dependency is unavailable.

Ubuntu WSL2 offline suite:

```powershell
wsl -d Ubuntu -- bash -lc 'cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend" && /home/zeeshan/netrca-venv/bin/python -m pytest -q'
```

Result: **104 passed, 24 skipped**, with the same deprecation warning and opt-in skip categories.

Windows combined opt-in PostgreSQL suite:

```powershell
$env:NETRCA_RUN_ANOMALY_DB_TESTS='1'; $env:NETRCA_RUN_CORRELATION_DB_TESTS='1'; $env:NETRCA_RUN_FAULT_DB_TESTS='1'; $env:NETRCA_RUN_IMPACT_DB_TESTS='1'; $env:NETRCA_RUN_PIPELINE_DB_TESTS='1'; $env:NETRCA_RUN_RCA_DB_TESTS='1'; $env:NETRCA_RUN_TOPOLOGY_DB_TESTS='1'; $env:NETRCA_RUN_SECURITY_DB_TESTS='1'; .\.venv\Scripts\python.exe -m pytest -q -m 'not mininet'
```

Result: **122 passed, 6 skipped**, one Starlette/httpx deprecation warning. Real PostgreSQL catalog/role checks, role-scoped CRUD rollback, and all enabled Phase 6/8/9/11/12 and topology database tests ran successfully. Skips were limited to tests requiring the separate real Mininet/lab opt-in and the optional scikit-learn-dependent test. No real Mininet test ran. No database fixture row remained after rollback verification.

Ubuntu WSL2 combined opt-in PostgreSQL suite used the equivalent environment flags and command:

```powershell
wsl -d Ubuntu -- bash -lc 'cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend" && NETRCA_RUN_ANOMALY_DB_TESTS=1 NETRCA_RUN_CORRELATION_DB_TESTS=1 NETRCA_RUN_FAULT_DB_TESTS=1 NETRCA_RUN_IMPACT_DB_TESTS=1 NETRCA_RUN_PIPELINE_DB_TESTS=1 NETRCA_RUN_RCA_DB_TESTS=1 NETRCA_RUN_TOPOLOGY_DB_TESTS=1 NETRCA_RUN_SECURITY_DB_TESTS=1 /home/zeeshan/netrca-venv/bin/python -m pytest -q -m "not mininet"'
```

Result: **122 passed, 6 skipped in 72.84 seconds**, with one Starlette/httpx deprecation warning. The same real Mininet/lab opt-in and optional scikit-learn tests were skipped. Live PostgreSQL checks and rollback tests passed in WSL2 as well.

`git diff --check` passed. No migration was needed or applied. No destructive SQL, deployment, commit, or push was performed. Real Mininet, live Gemini, and dependency vulnerability scanning were not run for the reasons above.

## Changed files

Phase 14 implementation and tests:

- `backend/app/core/middleware.py` (new)
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/app/api/network.py`
- `backend/app/db/connection.py`
- `backend/app/explanation/store.py`
- `backend/.env.example`
- `backend/tests/test_security_hardening.py` (new)
- `backend/tests/test_security_database_integration.py` (new)
- `backend/tests/test_database.py`
- `README.md`
- `security/PHASE14_REPORT.md` (new)

The pre-existing `.gitignore` edit (`Instructionn/`) remains untouched and unstaged. No original `Instruction/` document was modified. Final Git state is reported alongside this report; the Phase 14 work remains local for review.
