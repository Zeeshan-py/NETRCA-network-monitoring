import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { CorrelationLab } from "./correlation-lab";

afterEach(cleanup);

const events = [{ id: "event-1", event_type: "LINK_FAILURE", severity: "HIGH", timestamp: "2026-11-03T10:00:00Z", message: "Inter-switch link down" }];
const anomalies = [{ id: "anomaly-1", name: "Packet loss", severity: "HIGH", detected_at: "2026-11-03T10:00:10Z", model_name: "NETRCA_THRESHOLD", is_anomaly: true }];
const base = { events, anomalies, running: false, presentationMode: false, onCorrelate: vi.fn(), onRefresh: vi.fn(), onOpenIncident: vi.fn() };

test("submits only explicitly selected event and anomaly IDs", () => {
  const onCorrelate = vi.fn();
  render(<CorrelationLab {...base} onCorrelate={onCorrelate} />);
  fireEvent.click(screen.getByLabelText("Select event event-1"));
  fireEvent.click(screen.getByLabelText("Select anomaly anomaly-1"));
  fireEvent.click(screen.getByRole("button", { name: "Correlate selected evidence" }));
  expect(onCorrelate).toHaveBeenCalledWith(["event-1"], ["anomaly-1"]);
});

test("shows grounded relationship reasons and opens the produced incident", () => {
  const onOpenIncident = vi.fn();
  render(<CorrelationLab {...base} onOpenIncident={onOpenIncident} result={{ created: 1, attached: 2, skipped_ids: [], incidents: [{ incident_id: "incident-1", created: true, evidence: [{ kind: "EVENT", id: "event-1", reason: "SEED" }, { kind: "ANOMALY", id: "anomaly-1", reason: "SAME_LINK" }] }] }} />);
  expect(screen.getByText(/SAME LINK/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Open incident" }));
  expect(onOpenIncident).toHaveBeenCalledWith("incident-1");
});

test("keeps synthetic correlation explicitly labeled as a browser replay", () => {
  render(<CorrelationLab {...base} presentationMode />);
  expect(screen.getByText("Synthetic replay")).toBeInTheDocument();
  fireEvent.click(screen.getByLabelText("Select event event-1"));
  expect(screen.getByRole("button", { name: "Replay synthetic correlation" })).toBeEnabled();
});
