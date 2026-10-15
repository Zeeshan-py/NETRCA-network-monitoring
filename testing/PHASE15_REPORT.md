# NetRCA Phase 15 — End-to-End Integration Testing and Final Verification

**Verdict: PASS WITH FINDINGS**
**Branch:** `main`
**Commit/deployment:** none; changes remain local

The evidence path was exercised across the real FastAPI routes, isolated Ubuntu Mininet lab, and live PostgreSQL, with a deterministic provider stub and a rollback-only database transaction. One production integration defect was found and fixed. Live Gemini behavior remains unverified by design.

## Integration workflow

The opt-in test `backend/tests/test_e2e_workflow_database_integration.py` executed this request path:

1. Created the Phase 3 Mininet devices and links through the existing topology API.
2. Started the isolated lab through `POST /api/v1/network/start`.
3. Collected actual interface/link observations through `POST /api/v1/pipeline/collect` and a reachable host probe through `POST /api/v1/pipeline/probe`.
4. Submitted a controlled link-state observation, retrieved its stored metric, detected and persisted its anomaly, and submitted a directly related link-failure event.
5. Correlated the event and anomaly into one incident and retrieved its stored topology context.
6. Ran deterministic RCA and impact analysis, then called the real explanation API and explanation service with the provider selection method replaced by a deterministic test stub.
7. Confirmed the explanation referenced the current RCA and impact runs, returned only server-authored claims, and left the deterministic RCA result unchanged.
8. Rolled back the shared PostgreSQL transaction and verified the test device marker left no rows. TestClient shutdown stopped the Mininet network.

Final E2E result: **1 passed in 23.87 seconds**. No live Gemini request was made. The provider adapter's timeout, malformed-response, invalid-claim, and unavailable-credential cases remain covered by the existing mocked Phase 13 tests.

The first full workflow attempt exposed a real defect: `TopologyStore.load()` ran `SET TRANSACTION ... READ ONLY` after Phase 14's connection helper had already executed `SET LOCAL ROLE service_role`. PostgreSQL rejects setting transaction isolation after any statement has run, causing stored-topology and graph-context reads to fail. The fix moves isolation setup into the connection helper before role scoping, uses `read_only=True` for topology and paginated evidence reads, and uses `repeatable_read=True` for topology snapshot creation. A later attempt using a handwritten HTTP transport double returned the expected sanitized `GEMINI_UNAVAILABLE`; this was a mismatch in the test double, so the final E2E test stubs the provider selection boundary while retaining the real explanation service, context validation, and API route.

## Verification results

| Environment / command | Result |
| --- | --- |
| Windows backend offline suite, from `backend/`: `.venv\Scripts\python.exe -m pytest -q` | **106 passed, 25 skipped**, one Starlette/httpx deprecation warning. |
| Ubuntu WSL2 backend offline suite: `wsl -d Ubuntu -- bash -lc 'cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend" && /home/zeeshan/netrca-venv/bin/python -m pytest -q'` | **106 passed, 25 skipped**, same warning. |
| Windows opt-in PostgreSQL suite | **124 passed, 7 skipped**, one warning. Real catalog, RLS/role, persistence, idempotency, and rollback tests passed. |
| Ubuntu WSL2 equivalent opt-in PostgreSQL suite | **124 passed, 7 skipped**, one warning. |
| Ubuntu root-only Mininet suite: `NETRCA_RUN_MININET_TESTS=1 NETRCA_RUN_FAULT_TESTS=1 /home/zeeshan/netrca-venv/bin/python -m pytest -q tests/test_mininet_integration.py tests/test_monitoring_integration.py tests/test_faults_mininet_integration.py` | **4 passed in 8.47 seconds**: start/connectivity/reset/stop/retry, monitoring/probe, and controlled fault apply/recovery/expiry/stop cleanup. |
| Windows runner, real Mininet-to-PostgreSQL rollback test | **1 passed in 18.74 seconds**. Actual Mininet snapshot and probe reached PostgreSQL; the transaction rolled back. |
| Ubuntu root-only E2E: `NETRCA_RUN_E2E_DB_TESTS=1 /home/zeeshan/netrca-venv/bin/python -m pytest -q tests/test_e2e_workflow_database_integration.py` | **1 passed in 23.87 seconds**, including rollback. |
| Frontend, from `frontend/`: `npm test -- --run && npm run lint && npm run typecheck && npm run build` | **3 tests passed**; lint and typecheck passed; optimized Next.js production build completed. |
| `git diff --check` | Passed. |

The backend and frontend commands ran from their respective directories. Exact opt-in database/lab commands were:

```powershell
# Windows, from backend/
$env:NETRCA_RUN_ANOMALY_DB_TESTS='1'; $env:NETRCA_RUN_CORRELATION_DB_TESTS='1'; $env:NETRCA_RUN_FAULT_DB_TESTS='1'; $env:NETRCA_RUN_IMPACT_DB_TESTS='1'; $env:NETRCA_RUN_PIPELINE_DB_TESTS='1'; $env:NETRCA_RUN_RCA_DB_TESTS='1'; $env:NETRCA_RUN_TOPOLOGY_DB_TESTS='1'; $env:NETRCA_RUN_SECURITY_DB_TESTS='1'; .\.venv\Scripts\python.exe -m pytest -q -m 'not mininet'

# Ubuntu WSL2, from the repository root
wsl -d Ubuntu -- bash -lc 'cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend" && NETRCA_RUN_ANOMALY_DB_TESTS=1 NETRCA_RUN_CORRELATION_DB_TESTS=1 NETRCA_RUN_FAULT_DB_TESTS=1 NETRCA_RUN_IMPACT_DB_TESTS=1 NETRCA_RUN_PIPELINE_DB_TESTS=1 NETRCA_RUN_RCA_DB_TESTS=1 NETRCA_RUN_TOPOLOGY_DB_TESTS=1 NETRCA_RUN_SECURITY_DB_TESTS=1 /home/zeeshan/netrca-venv/bin/python -m pytest -q -m "not mininet"'

# Ubuntu WSL2, as root in the isolated lab, from backend/
wsl -d Ubuntu -u root -- bash -lc 'cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend" && NETRCA_RUN_MININET_TESTS=1 NETRCA_RUN_FAULT_TESTS=1 /home/zeeshan/netrca-venv/bin/python -m pytest -q tests/test_mininet_integration.py tests/test_monitoring_integration.py tests/test_faults_mininet_integration.py'

# Windows runner, from backend/, for the isolated WSL lab plus PostgreSQL rollback
$env:NETRCA_RUN_PIPELINE_LAB_TESTS='1'; .\.venv\Scripts\python.exe -m pytest -q tests/test_pipeline_mininet_database_integration.py

# Ubuntu WSL2, as root in the isolated lab, from backend/, full API workflow
wsl -d Ubuntu -u root -- bash -lc 'cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend" && NETRCA_RUN_E2E_DB_TESTS=1 /home/zeeshan/netrca-venv/bin/python -m pytest -q tests/test_e2e_workflow_database_integration.py'
```

The seven skips in each combined PostgreSQL run were the separately opted-in Mininet/lab and E2E cases plus the optional scikit-learn-dependent test. Those lab/E2E cases were then run separately as listed above; scikit-learn was unavailable, so its optional test remains skipped. The 25 offline-suite skips also include default-off PostgreSQL, Mininet/lab and E2E tests. No Mininet test was run from Windows directly.

After the Mininet and E2E runs, a read-only WSL check found no network namespaces, OVS bridges, or remaining Mininet processes. The lab was clean. Database test fixtures were rollback-only; no migration, schema modification, or persistent test data was left behind.

## Findings and remaining limitations

- Fixed the transaction-order defect described above. Regression coverage now checks isolation setup precedes `SET LOCAL ROLE`, and the end-to-end request path exercises stored graph context after collection and correlation.
- No other integration defect required a code change. Existing suites continued to validate invalid and duplicate evidence, unknown identifiers, disconnected topology, inconclusive outcomes, sanitized database/provider errors, local-control access, and rollback behavior.
- Gemini was mocked; provider access, account/model availability, and live upstream response behavior were not tested.
- NetRCA still uses the documented local-loopback controls rather than user authentication/RBAC. Do not expose it beyond the local development host without adding real identity and authorization.
- Starlette emits a deprecation warning for use of `httpx` with its test client; it does not fail the suites.
- PostgreSQL suites used the configured live database with rollback fixtures. All database changes in these tests were uncommitted transactional test data and were rolled back.

## Files changed

- `backend/app/db/connection.py` — transaction isolation configuration now precedes role scoping; supports repeatable-read snapshots.
- `backend/app/topology/store.py` — stored graph reads are explicitly read-only; snapshots request repeatable-read from the helper.
- `backend/app/pipeline/store.py` — paginated evidence listing uses the helper's read-only transaction.
- `backend/tests/test_database.py` — isolation ordering regression tests.
- `backend/tests/test_pipeline_database_integration.py` — transaction test double accepts transaction options.
- `backend/tests/test_topology_database_integration.py` — transaction test double accepts transaction options.
- `backend/tests/test_e2e_workflow_database_integration.py` — opt-in real Mininet/PostgreSQL complete API workflow with rollback.
- `testing/PHASE15_REPORT.md` — this report.

The Phase 13 and Phase 14 reports and existing phase reports were reviewed. No original `Instruction/` file was changed. No migration was applied. No commit, push, deployment, live Gemini request, or external-network fault was performed.

## Final Git status

The only unrelated pre-existing change is `.gitignore` (`Instructionn/`); it remains untouched and unstaged. Phase 15 files are local and uncommitted. `main` remains at `07c6f0b` and matches `origin/main` at the last status check. `git diff --check` passed.

```text
 M .gitignore  (pre-existing; preserved)
 M backend/app/db/connection.py
 M backend/app/pipeline/store.py
 M backend/app/topology/store.py
 M backend/tests/test_database.py
 M backend/tests/test_pipeline_database_integration.py
 M backend/tests/test_topology_database_integration.py
?? backend/tests/test_e2e_workflow_database_integration.py
?? testing/PHASE15_REPORT.md
```
