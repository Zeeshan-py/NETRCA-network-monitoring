# Phase 13 report — evidence-grounded Gemini incident explanation

## Implementation and contract

Phase 13 adds a local-only, opt-in FastAPI endpoint,
`POST /api/v1/ai/incidents/{incident_id}/explain`. It requires the established
loopback/origin guard and `X-NetRCA-Local-Control: 1`, plus
`NETRCA_GEMINI_ENABLED=true`. The backend reads a consistent, read-only
PostgreSQL snapshot of validated incident evidence, the latest current RCA
run, and any impact run for that exact RCA run. It verifies fingerprints,
incident/run relationships, evidence IDs and timestamps, and referenced
topology entities before making a provider request. Stale or mismatched
analysis returns a safe conflict response.

The versioned `EXPLANATION_INPUT_V1` is a bounded catalog of server-authored,
evidence-linked statements, with no raw log/event messages or secrets.
Gemini receives this as delimited data. Its only accepted response is a
complete ordering of the supplied claim IDs. Strict Pydantic and exact-set
validation reject model prose, fabricated claims, unknown/duplicate/omitted
IDs, and malformed output. The backend builds `EXPLANATION_V1` from its own
catalog. Thus every returned factual sentence has a stored-evidence or
deterministic-run reference. This conservative design means Gemini organizes
the explanation rather than freely writing it. No model tools, network
controls, remediation, or deterministic analysis changes are exposed.

The output separates observed facts, unconfirmed RCA candidates, potential
failure-chain exposure, observed versus potential impact, uncertainty,
missing impact analysis, and limitations. Inconclusive RCA/impact remains
explicit. Rule scores are not expressed as probabilities; user/application
impact remains unknown. See [README.md](README.md) for configuration,
contracts, representative claim, and response errors.

## Persistence and schema

The linked database target is project `oeizpptglvtnljkheatq`. Its existing
`public.ai_analyses` table has an incident FK but no constrained exact RCA or
impact run FK or explanation idempotency key. RLS is enabled with no client
policies; `service_role` has read/write privileges. A non-persistent response
meets the approved scope without a migration. No migration was created or
applied; `ai_analyses`, `recommendations`, and other tables were not changed.
The trade-off is that explanations cannot be retrieved later. The live
database currently has zero incidents, RCA runs, and impact runs, so a live
end-to-end explanation over stored data was unavailable.

## Files

Created: `backend/app/explanation/{__init__,models,store,context,provider,service}.py`,
`backend/app/api/ai.py`, `backend/tests/test_explanation.py`,
`explanation/{README,PHASE13_REPORT}.md`.

Modified: `backend/app/main.py`, `backend/app/core/config.py`,
`backend/requirements.txt`, `backend/.env.example`, and root `README.md`.
The original `Instruction/` files and pre-existing `.gitignore` edit were
preserved.

## Verification (2026-10-15)

- Windows, from `backend/`:
  `.\.venv\Scripts\python.exe -m pytest -q` — **100 passed, 20 skipped**.
- Ubuntu WSL2, from repository root:
  `wsl -d Ubuntu -- bash -lc 'cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend" && /home/zeeshan/netrca-venv/bin/python -m pytest -q'`
  — **100 passed, 20 skipped**.
- Windows, from `backend/`, with `NETRCA_RUN_RCA_DB_TESTS=1` and
  `NETRCA_RUN_IMPACT_DB_TESTS=1`:
  `.\.venv\Scripts\python.exe -m pytest tests/test_rca_database_integration.py tests/test_impact_database_integration.py -q`
  — **7 passed** against real PostgreSQL; fixtures rolled back.
- The Phase 13 `ExplanationStore.load` read-only transaction reached real
  PostgreSQL and returned the expected missing-incident condition for a
  nonexistent UUID. This is not an end-to-end stored-incident test.
- `.\.venv\Scripts\python.exe -m compileall -q app` — passed.
- `git diff --check` — passed (see final review).

The 20 default-suite skips comprise opt-in database, Mininet, and combined
integration tests, plus one anomaly test because scikit-learn is absent in
that environment. Real Mininet tests were unnecessary and were not run;
no lab was started. The provider adapter and endpoint were tested with fakes,
including credentials missing, rate limit, timeout, server error, malformed
output, unknown claims, injection-resistant input, access controls, and safe
errors. **No live Gemini call was made**; model access and provider behavior
with real credentials remain unverified.

No formatter, linter, or type checker is configured in this repository. The
existing FastAPI deprecation warning about `httpx`/`testclient` appeared in
both suites; it did not fail tests.

## Limitations and status

The endpoint has no saved-history/retrieval route. Gemini can reorder facts
but cannot add natural-language claims; this favors verifiable grounding over
generative prose. A live end-to-end explanation needs a stored incident with
current RCA and, optionally, impact results, an authorized backend key, and
explicit opt-in. The `gemini-2.5-flash` default is configurable and may depend
on account model access. There are no Phase 13 database writes. No Phase 14
work, commit, push, or deployment was performed.
