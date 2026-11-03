import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ImpactLab } from "./impact-lab";
import type { ImpactRun, IncidentDetail, RcaRun } from "@/lib/api";

afterEach(cleanup);

const incident = { id: "incident-1", title: "Inter-switch outage", severity: "HIGH", status: "DETECTED", start_time: "2026-11-03T10:00:00Z" };
const detail: IncidentDetail = { ...incident, events: [{ id: "event-1" }], anomalies: [{ id: "anomaly-1" }] };
const rca: RcaRun = { id: "rca-1", incident_id: incident.id, analysis_version: "RULES_V1", input_fingerprint: "hash", status: "CANDIDATES", created_at: incident.start_time, last_analyzed_at: incident.start_time, result: { incident_id: incident.id, status: "CANDIDATES", candidates: [], limitations: [], evidence_count: 2, analysis_version: "RULES_V1" } };
const impact: ImpactRun = { id: "impact-1", rca_run_id: rca.id, analysis_version: "IMPACT_RULES_V1", input_fingerprint: "input", topology_fingerprint: "topology", status: "ASSESSED", created_at: incident.start_time, last_analyzed_at: incident.start_time, result: { incident_id: incident.id, rca_run_id: rca.id, status: "ASSESSED", candidate_target_kind: "LINK", candidate_target_id: "link-1", affected_devices: 1, affected_links: 1, affected_services: 1, user_application_impact: "UNKNOWN_UNVERIFIED", topology_input: {}, limitations: ["CURRENT_TOPOLOGY_NOT_HISTORICAL"], analysis_version: "IMPACT_RULES_V1", entities: [{ kind: "LINK", id: "link-1", classification: "OBSERVED", explanation: "Direct link failure evidence", evidence: [{ source_type: "EVENT", source_id: "event-1", reason: "DIRECT_FAILURE" }] }, { kind: "DEVICE", id: "device-1", classification: "POTENTIAL", explanation: "One-hop endpoint exposure", evidence: [{ source_type: "EVENT", source_id: "event-1", reason: "DIRECT_FAILURE" }] }], chain: [{ step: 1, source_kind: "LINK", source_id: "link-1", target_kind: "DEVICE", target_id: "device-1", relationship: "LINK_ENDPOINT", classification: "POTENTIAL", explanation: "Physical endpoint", evidence: [{ source_type: "EVENT", source_id: "event-1", reason: "DIRECT_FAILURE" }] }] } };

const base = { incidents: [incident], selectedId: incident.id, detail, rca, result: impact, loading: false, running: false, error: undefined, presentationMode: false, onSelect: vi.fn(), onRun: vi.fn(), onOpenRca: vi.fn(), onOpenTopology: vi.fn() };

test("runs impact only for the selected incident with a stored RCA", () => {
  const onRun = vi.fn();
  render(<ImpactLab {...base} onRun={onRun} />);
  fireEvent.click(screen.getByRole("button", { name: "Run impact analysis" }));
  expect(onRun).toHaveBeenCalledWith("incident-1");
});

test("distinguishes observed evidence from potential structural exposure", () => {
  render(<ImpactLab {...base} />);
  expect(screen.getByText(/Observed: directly reported/)).toBeInTheDocument();
  expect(screen.getByText(/Potential: structural exposure only/)).toBeInTheDocument();
  expect(screen.getByText(/Steps order structural exposure/)).toBeInTheDocument();
  expect(screen.getByText(/No incident-scoped customer/)).toBeInTheDocument();
});

test("preserves inconclusive impact without affected entities", () => {
  const inconclusive = { ...impact, status: "INCONCLUSIVE" as const, result: { ...impact.result, status: "INCONCLUSIVE" as const, entities: [], chain: [], affected_devices: 0, affected_links: 0, affected_services: 0 } };
  render(<ImpactLab {...base} result={inconclusive} />);
  expect(screen.getByText("Inconclusive by design")).toBeInTheDocument();
  expect(screen.getByText("No defensible affected entity was produced.")).toBeInTheDocument();
});

test("blocks analysis until a stored RCA exists and labels presentation replay", () => {
  render(<ImpactLab {...base} rca={undefined} result={undefined} presentationMode />);
  expect(screen.getByRole("button", { name: "Replay synthetic impact" })).toBeDisabled();
  expect(screen.getByText(/Run deterministic RCA before impact analysis/)).toBeInTheDocument();
  expect(screen.getByText("Synthetic replay")).toBeInTheDocument();
});
