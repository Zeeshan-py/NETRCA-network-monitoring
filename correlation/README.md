# Phase 9 event correlation and incident grouping

Phase 9 groups explicitly related, validated **stored** Phase 6 events and Phase 8 metric anomalies. It does not infer a root cause, graph path, impact, or AI confidence, and does not start Mininet. The engine in `backend/app/correlation/engine.py` is pure Python; `store.py` handles PostgreSQL reads and one transactional write; `api/incidents.py` handles local API access.

## Correlation rules

`POST /api/v1/events/correlate` accepts up to 100 stored UUIDs in `event_ids` and `anomaly_ids`. Phase 6 events must still pass the Phase 6 `EventIn` source/dedup/timestamp validation. Phase 8 anomalies must be positive `NETRCA_` findings backed by a valid Phase 6 metric; the recorded observed time must match that metric's timestamp. Unknown, malformed, future, or stale evidence is rejected or skipped. The default maximum observation age is 24 hours (`NETRCA_CORRELATION_MAX_AGE_MINUTES`); the default pairwise window is 300 seconds (`NETRCA_CORRELATION_WINDOW_SECONDS`). Both are bounded settings.

Time proximity is necessary but never sufficient. Within the window, the rules are: source event reference (`SOURCE_EVENT`), shared source metric between anomalies (`SOURCE_METRIC`), same link (`SAME_LINK`), same service (`SAME_SERVICE`), same device (`SAME_DEVICE`), or a direct device endpoint of the evidence's known stored link (`LINK_ENDPOINT`). Two distinct explicit service IDs block grouping. Unknown link endpoints and global collection failures do not produce a topology relationship. No multi-hop traversal or name-based dependency guess is used. The whole group's first-to-last observation span cannot exceed the window. Duplicate UUIDs are processed once.

Each new group creates a `DETECTED` incident. A group can attach to a `DETECTED` or `INVESTIGATING` incident only when an item directly relates to its stored evidence in the window. Groups that match multiple existing incidents are skipped rather than merging incidents. Closed/resolved incident membership is preserved; reprocessing cannot reopen it. Existing incident status is not changed. Severity is the highest `LOW < MEDIUM < HIGH < CRITICAL` across its current severity and new evidence; optional missing severity normalizes to `LOW` in the pure engine, while invalid stored rows are rejected. The start time moves earlier if older valid evidence is attached. Root-cause, confidence, impact, end-time, and AI fields are never populated by Phase 9.

The repository uses `pg_advisory_xact_lock(47301, 9)` to serialize Phase 9 runs across workers. Existing memberships are checked before insertion; the approved `incident_anomalies` unique anomaly key and existing `incident_events` unique incident/event key provide database protection. Every change commits or rolls back as one transaction. Phase 8 source records are never modified. `relationship_type` stores the direct rule or `SEED` for the first item. When an item is already present, the structured response marks it `EXISTING` without rewriting its stored reason.

## Local API

Set `NETRCA_CORRELATION_WRITES_ENABLED=true` in backend configuration to allow writes. All three routes require a loopback caller and the existing local-origin policy. The POST additionally requires `X-NetRCA-Local-Control: 1`.

```http
POST /api/v1/events/correlate
X-NetRCA-Local-Control: 1
Content-Type: application/json

{"event_ids":["<stored-event-uuid>"],"anomaly_ids":["<stored-anomaly-uuid>"]}
```

```json
{"success":true,"data":{"incidents":[{"incident_id":"<uuid>","created":true,"evidence":[{"kind":"EVENT","id":"<uuid>","reason":"SEED"}]}],"skipped_ids":[],"created":1,"attached":1}}
```

`GET /api/v1/incidents?page=1&limit=20&status=DETECTED&severity=HIGH` returns `success`, `data`, and `pagination` (`page`, `limit`, `total`, `pages`). `GET /api/v1/incidents/{incident_id}` returns the incident and its original event/anomaly IDs, timestamps, resource IDs, source metric/event IDs, and stored relationship reasons. An unknown incident returns 404. Invalid filters return 422. An unavailable database returns a sanitized 503; no persistence is claimed on failure.

## Database and validation

The additive migration is `supabase/migrations/20261013000102_phase9_incident_anomalies.sql`. It was approved separately and applied only to the verified linked project with `npx supabase migration up --linked`; no `db push` or seed was used. The table has incident/anomaly foreign keys, a composite primary key, a unique anomaly key, a nonempty relationship reason, timestamp/index, RLS, no client policies, and service-role grants. See [PHASE9_REPORT.md](PHASE9_REPORT.md) for exact verification and test results.

From `backend/`, run offline tests with `.venv/Scripts/python.exe -m pytest -q` on Windows or the configured Linux virtual environment under WSL2. Opt into the real rollback integration test with `NETRCA_RUN_CORRELATION_DB_TESTS=1` and `python -m pytest -q tests/test_correlation_database_integration.py`. A reachable configured `DATABASE_URL` is required. The test inserts unique Phase 6/8/9 rows in a transaction and rolls them back; it does not seed the remote database. Do not enable the write flag on a remotely accessible API process; the current security boundary is for local development, not production authentication.
