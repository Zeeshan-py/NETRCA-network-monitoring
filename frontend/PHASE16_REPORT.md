# Phase 16 — Frontend-to-Backend Integration and Demo Readiness

## Executive verdict: PASS WITH FINDINGS

The frontend now reads the existing local FastAPI contracts for network status, topology, monitoring, stored evidence, anomalies, and incidents. Incident detail loads its original event/anomaly references and the current RCA and impact results; explicit controls invoke the existing correlation, RCA, impact, and explanation endpoints. No backend, schema, or database files were changed.

The real browser smoke exercised read-only requests against the local API and rendered the currently empty database/lab states. It did not perform write actions, start Mininet, contact Gemini, or complete an end-to-end investigation. The UI presents topology as device/link tables rather than a spatial graph, and there is no dedicated probe-result or fault-injection UI. These are remaining presentation/workflow limits; the backend API has not been expanded.

## Integrated UI and API

The dashboard sections are **Overview**, **Topology**, **Evidence**, **Anomalies**, and **Incidents**. The API client uses the configured `NEXT_PUBLIC_API_BASE_URL` and integrates:

- `GET /health`, `/network/status`, `/topology`, `/topology?source=stored`, and `/network/monitoring`.
- Paginated `GET /metrics`, `/logs`, `/events`, `/anomalies`, and `/incidents`.
- `GET /incidents/{id}`, `/incidents/{id}/root-causes`, and `/incidents/{id}/impact`.
- Explicit protected operations: `POST /events/correlate`, `/incidents/{id}/root-cause/analyze`, `/incidents/{id}/impact/analyze`, and `/ai/incidents/{id}/explain`.

The API client normalizes the two pagination envelope shapes present in the backend. If live topology is unavailable because Mininet is disabled/unavailable, it requests the stored topology. Other failures remain visible as errors. Incident selection and refresh use abort signals to prevent stale responses from replacing newer state. No automatic polling is used.

Root-cause candidate scores are labeled uncalibrated rule points, not probabilities. Impact is presented from the existing response and its evidence status is preserved. Explanation generation occurs only after an explicit button click. There are no fault-injection controls in the UI; none were added.

## Data, states, and security

Runtime pages use backend responses only; there is no runtime demonstration dataset. The component/API tests use mocked responses only for isolated tests. The UI implements loading, empty, success, and error states. Tests exercised successful and empty API-backed rendering, database/API errors, 403/422 responses, malformed URL configuration, network failure, pagination envelope variants, topology fallback, and protected-header behavior. The real browser smoke confirmed successful API connectivity and empty states for all five sections, including stored topology fallback while Mininet was disabled. A malformed successful payload and a deferred loading-state assertion are not separately covered by the current tests.

The browser client does not receive database or Gemini credentials. The established `X-NetRCA-Local-Control: 1` header is sent only for explicit protected actions. Backend write flags and local-only checks remain authoritative; this change does not bypass them. No protected action was triggered during the browser smoke. The configured CORS origin must exactly match the browser origin: `http://localhost:3000` worked with the local backend configuration, while using `http://127.0.0.1:3000` produced denied requests. Keep both servers bound to loopback and do not expose this unauthenticated application to a LAN or public network.

## Demo procedure and execution

The local procedure is in the root README under **Local demonstration workflow**. It covers local environment configuration, starting both processes, checking health and sections independently, using only a disposable local database for fixtures, guarded Mininet use, explicit analysis/explanation actions, empty/error states, and shutdown.

Executed: started the local API and Next.js development server, opened the dashboard at `http://localhost:3000`, and navigated through Overview, Topology, Evidence, Anomalies, and Incidents. The browser displayed API-connected and empty-data states; the disabled simulator correctly fell back to the stored topology. Both local processes were stopped after the smoke test. This was a read-only UI smoke, not the full seeded Mininet/PostgreSQL/Gemini demonstration.

## Verification

Commands run from `frontend/`:

- `npm test -- --run` — **12 passed**, 3 test files; 0 failed.
- `npm run lint` — **passed**; 0 reported errors.
- `npm run typecheck` — **passed** (`next typegen` and `tsc --noEmit`).
- `npm run build` — **passed**; static `/` and `/_not-found` routes generated.
- Local browser smoke — **passed for read-only connectivity and rendering**, with the limits above.
- `git diff --check` — **passed** (exit code 0).

Not run: backend regression tests, PostgreSQL rollback/E2E tests, live Mininet tests, fault injection, and live Gemini. No backend API behavior was modified; the simulator was disabled in the observed Windows environment; and the user prohibited Gemini calls and disruptive real-network activity. The seeded end-to-end workflow was not claimed or run.

## Files changed

- `frontend/src/lib/api.ts` — typed API response helpers, backend envelope normalization, safe URL/error handling, topology fallback, and calls for existing incident actions.
- `frontend/src/components/dashboard.tsx` — API-backed dashboard sections, pagination, loading/empty/error states, evidence-linked incident detail, and explicit analysis actions.
- `frontend/src/app/page.tsx` — renders the integrated dashboard.
- `frontend/src/app/globals.css` — dashboard layout and responsive styles.
- `frontend/src/lib/api.test.ts` — API client contract, pagination, topology fallback, security-header, validation, and network failure tests.
- `frontend/src/app/page.test.tsx` — component coverage for API-backed views, empty/error states, incident evidence, candidate labeling, and explicit explanation behavior.
- `README.md` — Phase 16 scope and local demo procedure.
- `frontend/PHASE16_REPORT.md` — this report.

## Limitations and unverified workflows

- Topology is displayed as device/link tables; no spatial graph renderer was added.
- The API supports an on-demand probe, but no dedicated probe-result control/panel was added. Monitoring snapshots and stored probe-derived metrics/events are displayed through existing routes.
- No fault controls are exposed. No attempt was made to enable or run faults.
- The local database had no stored records in the browser smoke; incident detail/actions with real records were covered only through mocked component tests.
- Correlation, RCA, impact, and explanation controls were not clicked in the browser. Their frontend request contracts and local-control header behavior are covered by API-client tests; actual backend write configurations were not changed.
- A live database transaction/rollback, Mininet integration, and provider-backed explanation were not verified in this phase.

## Git state

Branch: `main`, still at `8b97d79` (`Complete Phase 15 end-to-end verification`); no commit or push was made. Final changes are unstaged. Modified tracked files: `README.md`, `frontend/src/app/globals.css`, `frontend/src/app/page.test.tsx`, `frontend/src/app/page.tsx`, and `frontend/src/lib/api.ts`. New untracked files: `frontend/PHASE16_REPORT.md`, `frontend/src/components/dashboard.tsx`, and `frontend/src/lib/api.test.ts`.

The pre-existing `.gitignore` modification remains untouched and unstaged. No `Instruction/` files, backend files, migrations, or environment settings were changed. There are no staged changes.
