import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ExplanationLab } from "./explanation-lab";
import type { IncidentDetail, IncidentExplanation, RcaRun } from "@/lib/api";

afterEach(cleanup);

const incident = { id: "incident-1", title: "Inter-switch outage", severity: "HIGH", status: "DETECTED", start_time: "2026-11-03T10:00:00Z" };
const detail: IncidentDetail = { ...incident, events: [{ id: "event-1" }], anomalies: [{ id: "anomaly-1" }] };
const rca: RcaRun = { id: "rca-1", incident_id: incident.id, analysis_version: "RULES_V1", input_fingerprint: "hash", status: "CANDIDATES", created_at: incident.start_time, last_analyzed_at: incident.start_time, result: { incident_id: incident.id, status: "CANDIDATES", candidates: [], limitations: [], evidence_count: 2, analysis_version: "RULES_V1" } };
const claim = { claim_id: "C001", section: "summary" as const, text: "The deterministic analysis ranks the failed link as a candidate.", evidence_references: [{ source_type: "RCA_RUN" as const, source_id: rca.id, timestamp: incident.start_time }] };
const explanation: IncidentExplanation = { explanation_version: "EXPLANATION_V1", incident_id: incident.id, rca_run_id: rca.id, impact_run_id: null, model_name: "gemini-test", summary: [claim], observed_facts: [], candidate_explanations: [], failure_chain_explanation: [], impact_explanation: [], uncertainties: [], missing_evidence: [], limitations: [], evidence_references: claim.evidence_references };
const base = { incidents: [incident], selectedId: incident.id, detail, rca, impact: undefined, explanation, loading: false, generating: false, error: undefined, presentationMode: false, onSelect: vi.fn(), onGenerate: vi.fn(), onOpenRca: vi.fn(), onOpenImpact: vi.fn() };

test("generates only for the explicitly selected incident after RCA", () => {
  const onGenerate = vi.fn();
  render(<ExplanationLab {...base} onGenerate={onGenerate} />);
  fireEvent.click(screen.getByRole("button", { name: "Generate explanation with Gemini" }));
  expect(onGenerate).toHaveBeenCalledWith("incident-1");
});

test("shows the claim-ordering trust boundary and evidence provenance", () => {
  render(<ExplanationLab {...base} />);
  expect(screen.getByText("Backend authors claims")).toBeInTheDocument();
  expect(screen.getByText("Model orders IDs")).toBeInTheDocument();
  expect(screen.getByText(claim.text)).toBeInTheDocument();
  fireEvent.click(screen.getByText("1 evidence reference"));
  expect(screen.getAllByText(rca.id).length).toBeGreaterThanOrEqual(2);
});

test("blocks generation without deterministic RCA", () => {
  render(<ExplanationLab {...base} rca={undefined} explanation={undefined} />);
  expect(screen.getByRole("button", { name: "Generate explanation with Gemini" })).toBeDisabled();
  expect(screen.getByText(/Gemini cannot replace root-cause analysis/)).toBeInTheDocument();
});

test("labels presentation output as a static no-provider replay", () => {
  render(<ExplanationLab {...base} presentationMode />);
  expect(screen.getByText("Static explanation replay")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Show static explanation" })).toBeEnabled();
});
