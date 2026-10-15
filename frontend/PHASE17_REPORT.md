# Phase 17 — Interactive Topology Visualization and Evidence Navigation

**Verdict: PASS WITH FINDINGS.** The read-only frontend graph and navigation flows are implemented and the frontend verification suite passes. The real API smoke test confirmed that the stored topology contract works but currently has no stored devices or links; live Mininet is disabled, so populated live graph interactions could not be verified against runtime data.

## APIs and data contracts

- `GET /api/v1/topology/analysis?source=live|stored` supplies an undirected `PHYSICAL_TOPOLOGY` graph with `connected`, `components`, devices (`id`, `name`, `device_type`, optional `status`) and links (`id`, `source_device_id`, `destination_device_id`, optional `status`). The client validates the response and rejects duplicate graph IDs. Links whose endpoints are absent are omitted from the drawing and surfaced as a partial-graph warning.
- `GET /api/v1/incidents/{id}/topology-context` supplies stored incident evidence references, directly referenced device/link IDs, one-hop stored context IDs, missing IDs, and unmapped service IDs. The client validates the incident identity and stored source before showing context.
- Existing paginated `GET /api/v1/metrics`, `/logs`, `/events`, and `/anomalies` accept existing `device_id` filters. Metrics and events also accept existing `link_id` filters. The UI uses only those supported filters.

No backend routes, database schema, or API response models were changed. Graph responses have no observation timestamp, so the UI explicitly reports that freshness is unavailable rather than labeling graph data fresh or stale.

## Visualization and navigation

The topology view renders devices as selectable SVG nodes and links as selectable edges, with deterministic layout, disconnected-component handling, zoom, pan, fit/reset, and keyboard selection. Status colors use values from the API; missing or unrecognized status is shown as unknown. Device and link details show only graph fields returned by the API.

Live Mininet and stored topology are separate sources. Switching source aborts the previous request and clears selections and incident context. Runtime Mininet identifiers are not matched to stored database identifiers because no supported mapping is exposed by the APIs.

For a selected stored device, users can browse its metrics, logs, events, and anomalies. For a selected stored link, users can browse metrics and events. These views use the backend's existing ID filters and do not infer incident membership. Users can browse incident history. From an incident detail, an explicit action retrieves and highlights only the backend's validated stored topology context; missing references are disclosed. There is no direct device/link-to-incident API relationship, so the interface does not claim one.

Loading, API error, empty graph, missing status, invalid endpoint, and disconnected graph states are represented. Failed or superseded requests do not leave stale graph/context displayed. The graph is read-only and does not invoke network control, fault injection, or Gemini actions.

## Security and scope

Only existing read-only endpoints are used for graph and context retrieval. Existing local-control headers, write flags, authentication boundaries, and backend security settings were not changed. No credentials or privileged environment values were added to browser code. No migration, backend implementation, Phase 18 work, commit, or push was performed.

## Verification

Commands run from `frontend/` on Windows:

- `npm test -- --run --reporter=dot` — **passed**, 6 test files and 30 tests.
- `npm run lint` — **passed**.
- `npm run typecheck` — **passed**.
- `npm run build` — **passed**; static `/` and `/_not-found` routes generated.

`git diff --check` — **passed**. No backend tests or Mininet tests were run because Phase 17 changes are frontend-only and the task did not require network mutation. Ubuntu WSL2 tests were not run; all requested frontend checks ran on Windows. Populated graph selection and live source behavior remain unverified against real topology data because stored topology is empty and the live source returned `SIMULATION_DISABLED` (HTTP 503). No incident records were available to exercise live incident-context navigation in the browser; those cases are covered by component/API tests.

Browser smoke test against the local frontend and real local API:

- Dashboard reported `API connected`.
- `GET /api/v1/topology/analysis?source=stored` returned HTTP 200 with a valid empty graph (`connected: false`, zero components, devices, and links); the UI showed the corresponding disconnected empty state and noted that freshness timestamp is not supplied.
- The live-source request returned HTTP 503 because Mininet simulation is disabled. No attempt was made to enable or start it.

## Files changed

- `frontend/src/lib/api.ts` and `frontend/src/lib/api.test.ts` — graph/context contracts, validation, and supported evidence filters.
- `frontend/src/lib/topology-graph.ts` and `frontend/src/lib/topology-graph.test.ts` — deterministic graph layout and endpoint handling.
- `frontend/src/components/topology-explorer.tsx` and its tests — interactive SVG graph, source selection, status and context states.
- `frontend/src/components/topology-evidence.tsx` and its tests — paginated navigation to stored evidence.
- `frontend/src/components/dashboard.tsx`, `frontend/src/app/globals.css`, and `frontend/src/app/page.test.tsx` — dashboard integration, styling, and source/context flows.
- `README.md` — Phase 17 scope and report link.
- `frontend/PHASE17_REPORT.md` — this report.

## Final repository state

Branch remains `main`, aligned with `origin/main`; no files are staged. Phase 17 files listed above are local working-tree changes. The pre-existing `.gitignore` modification remains untouched and unstaged. Temporary local frontend/backend servers used for the smoke test were stopped. Next.js-generated `frontend/AGENTS.md` and the generated `frontend/next-env.d.ts` change were removed/restored after verification. No commit or push was made.
