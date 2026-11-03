import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { RcaLab } from "./rca-lab";
import type { IncidentDetail, RcaRun } from "@/lib/api";

afterEach(cleanup);

const incident = { id: "incident-1", title: "Inter-switch outage", severity: "HIGH", status: "DETECTED", start_time: "2026-11-03T10:00:00Z" };
const detail: IncidentDetail = { ...incident, description: "Stored correlated evidence", events: [{ id: "event-1", event_type: "LINK_FAILURE" }], anomalies: [{ id: "anomaly-1", name: "Packet loss" }] };
const run: RcaRun = { id: "run-1", incident_id: incident.id, analysis_version: "RULES_V1", input_fingerprint: "hash", status: "CANDIDATES", created_at: "2026-11-03T10:01:00Z", last_analyzed_at: "2026-11-03T10:01:00Z", result: { incident_id: incident.id, status: "CANDIDATES", evidence_count: 2, analysis_version: "RULES_V1", limitations: ["Stored topology may be newer than evidence"], candidates: [{ cause_type: "LINK_FAILURE", target_kind: "LINK", target_id: "link-1", score: 6, score_kind: "UNCALIBRATED_RULE_POINTS", explanation: "Direct link failure preceded related symptoms.", contributions: [{ rule: "DIRECT_FAILURE", points: 4, evidence: [{ source_type: "EVENT", source_id: "event-1", reason: "DIRECT_FAILURE" }] }], supporting_evidence: [{ source_type: "EVENT", source_id: "event-1", timestamp: "2026-11-03T10:00:00Z", reason: "DIRECT_FAILURE" }], contradictory_evidence: [], limitations: [] }] } };

const base = { incidents: [incident], selectedId: incident.id, detail, result: run, loading: false, running: false, error: undefined, presentationMode: false, onSelect: vi.fn(), onRun: vi.fn(), onOpenTopology: vi.fn() };

test("runs RCA only for the explicitly selected incident", () => {
  const onRun = vi.fn();
  render(<RcaLab {...base} onRun={onRun} />);
  fireEvent.click(screen.getByRole("button", { name: "Run deterministic RCA" }));
  expect(onRun).toHaveBeenCalledWith("incident-1");
});

test("shows rank, rule score meaning, contributions, provenance, and limitations", () => {
  render(<RcaLab {...base} />);
  expect(screen.getByText("RANK 1")).toBeInTheDocument();
  expect(screen.getByText(/not probability or confidence/i)).toBeInTheDocument();
  expect(screen.getByText("+4")).toBeInTheDocument();
  expect(screen.getAllByText(/DIRECT FAILURE/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/Stored topology may be newer/)).toBeInTheDocument();
});

test("preserves an inconclusive result without inventing a candidate", () => {
  const inconclusive = { ...run, status: "INCONCLUSIVE" as const, result: { ...run.result, status: "INCONCLUSIVE" as const, candidates: [], limitations: ["NO_DIRECT_FAILURE_EVIDENCE"] } };
  render(<RcaLab {...base} result={inconclusive} />);
  expect(screen.getByText("Inconclusive by design")).toBeInTheDocument();
  expect(screen.getByText("No supported candidate was produced.")).toBeInTheDocument();
  expect(screen.queryByText("RANK 1")).not.toBeInTheDocument();
});

test("labels presentation analysis as a static replay", () => {
  render(<RcaLab {...base} presentationMode />);
  expect(screen.getByText("Synthetic replay")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Replay synthetic RCA" })).toBeEnabled();
});
