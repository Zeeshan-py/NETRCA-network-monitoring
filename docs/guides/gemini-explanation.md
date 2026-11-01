# Phase 13 — Evidence-grounded Gemini incident explanation

`POST /api/v1/ai/incidents/{incident_id}/explain` explains the latest stored
Phase 11 RCA run and its matching Phase 12 impact run, if one exists. It is
loopback-only, requires `X-NetRCA-Local-Control: 1`, and requires
`NETRCA_GEMINI_ENABLED=true`. It does not save explanations. There is no
retrieval endpoint, network control, SQL mutation, remediation, or Gemini tool.

Set `GEMINI_API_KEY` only in the backend environment. The default model is
`gemini-2.5-flash`, configurable through `NETRCA_GEMINI_MODEL`. Account access
to that model is provider-dependent. `NETRCA_GEMINI_TIMEOUT_SECONDS` defaults
to 15 (allowed 2–30). A missing key, timeout, rate limit, malformed response,
or provider failure yields `503 GEMINI_UNAVAILABLE` without exposing upstream
body or credentials. A missing RCA run yields `409 RCA_REQUIRED`; stale or
inconsistent evidence yields `409 ANALYSIS_NOT_READY`.

`EXPLANATION_INPUT_V1` contains incident/RCA/impact run IDs and up to 80
server-authored claims. Each claim has a category, text, and typed evidence
references with timestamps when available. The input is capped at 12 KiB. Raw
event/log messages, credentials, and unrelated incident data are excluded.
The store reads validated incident evidence and runs in one repeatable-read,
read-only PostgreSQL transaction. It rejects stale RCA fingerprints, changed
topology, mismatched run IDs, unknown evidence, and unsupported entity IDs.

Gemini receives this catalog as data with no tools. Its strict JSON response
must contain `ordered_claim_ids`: a permutation of **all and only** supplied
IDs. The backend renders the claims from its own catalog into `EXPLANATION_V1`.
This deliberately limits Gemini to organizing facts; it cannot add prose,
measurements, identifiers, or causal assertions to the public response.
Unknown, repeated, omitted, or malformed claim IDs invalidate the response.
The model is not an authoritative RCA or impact engine.

The response `data` contains `explanation_version`, `incident_id`,
`rca_run_id`, optional `impact_run_id`, `model_name`, claim arrays named
`summary`, `observed_facts`, `candidate_explanations`,
`failure_chain_explanation`, `impact_explanation`, `uncertainties`,
`missing_evidence`, and `limitations`, plus deduplicated
`evidence_references`. Every claim includes its own references. For example,
an inconclusive RCA summary is represented as:

```json
{
  "claim_id": "C001",
  "section": "summary",
  "text": "The deterministic RCA is inconclusive; no root cause is confirmed.",
  "evidence_references": [{
    "source_type": "RCA_RUN",
    "source_id": "00000000-0000-0000-0000-000000000007",
    "timestamp": "2026-10-15T00:00:00Z"
  }]
}
```

`OBSERVED` is a direct incident-evidence label from Phase 12. `POTENTIAL`
denotes exposure only; it never establishes outage or propagation. RCA
candidates remain candidates, and rule points are not probabilities.

Phase 13 does not write `public.ai_analyses` or `public.recommendations`.
The existing `ai_analyses` schema has no constrained references to exact RCA
and impact runs or an idempotency key. An ephemeral response meets this scope
without a migration, but cannot be retrieved later. Persistence would need
separately approved provenance constraints and access rules.
