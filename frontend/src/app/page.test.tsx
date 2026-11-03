import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import Home from "./page";

const api = vi.hoisted(() => ({
  getApiHealth: vi.fn(), getNetworkStatus: vi.fn(), getTopology: vi.fn(), getMonitoring: vi.fn(),
  getPage: vi.fn(), getIncident: vi.fn(), getIncidentRca: vi.fn(), getIncidentImpact: vi.fn(),
  getTopologyGraph: vi.fn(), getIncidentTopologyContext: vi.fn(),
  getFaultTypes: vi.fn(), getFaults: vi.fn(), injectFault: vi.fn(), recoverFault: vi.fn(), resetFaults: vi.fn(),
  collectEvidenceSnapshot: vi.fn(), collectEvidenceProbe: vi.fn(), detectStoredMetrics: vi.fn(),
  runIncidentRca: vi.fn(), runIncidentImpact: vi.fn(), correlateEvidence: vi.fn(), generateIncidentExplanation: vi.fn(),
  startNetwork: vi.fn(), stopNetwork: vi.fn(), resetNetwork: vi.fn(), testNetworkConnectivity: vi.fn(), probeNetwork: vi.fn(),
}));
vi.mock("@/lib/api", () => api);

afterEach(() => { cleanup(); vi.clearAllMocks(); });

function healthyResponses() {
  api.getApiHealth.mockResolvedValue({ data: { api: "UP" } });
  api.getNetworkStatus.mockResolvedValue({ data: { state: "RUNNING", topology_name: "lab", device_count: 2, link_count: 1 } });
  api.getTopology.mockResolvedValue({ data: { nodes: [{ id: "d1", name: "h1", device_type: "HOST", state: "PRESENT" }], links: [] } });
  api.getMonitoring.mockResolvedValue({ data: { observed_at: "2026-10-15T10:00:00Z", network_state: "RUNNING", collection_status: "COMPLETE", devices: [], links: [], errors: [] } });
  api.getTopologyGraph.mockResolvedValue({ data: { directed: false, semantics: "PHYSICAL_TOPOLOGY", connected: true, components: [["d1"]], devices: [{ id: "d1", name: "h1", device_type: "HOST", status: "PRESENT" }], links: [] } });
  api.getFaultTypes.mockResolvedValue({ data: ["INTERFACE_FAILURE", "LINK_FAILURE", "PACKET_LOSS", "HIGH_LATENCY"] });
  api.getFaults.mockResolvedValue({ data: [], pagination: { page: 1, limit: 100, total: 0, pages: 0 } });
  api.getPage.mockImplementation(async (resource: string) => ({ data: resource === "incidents" ? [] : [], pagination: { page: 1, limit: 20, total: 0, pages: 0 } }));
}

test("loads real API-backed overview and presents empty evidence honestly", async () => {
  healthyResponses();
  render(<Home />);
  expect(await screen.findByText("API connected")).toBeInTheDocument();
  expect(screen.getByText("RUNNING")).toBeInTheDocument();
  expect(screen.getByText("h1")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Evidence" }));
  expect(await screen.findAllByText("No stored records are available yet.")).toHaveLength(3);
});

test("starts the controlled lab and refreshes the live topology", async () => {
  healthyResponses();
  api.getNetworkStatus.mockResolvedValue({ data: { state: "STOPPED", topology_name: "netrca_lab_v1", device_count: 0, link_count: 0, operation: null } });
  api.startNetwork.mockResolvedValue({ data: { state: "RUNNING", topology_name: "netrca_lab_v1", device_count: 5, link_count: 4, operation: null } });
  render(<Home />);
  fireEvent.click(screen.getByRole("button", { name: "Topology" }));
  const start = await screen.findByRole("button", { name: "Start lab" });
  await waitFor(() => expect(start).toBeEnabled());
  fireEvent.click(start);
  await waitFor(() => expect(api.startNetwork).toHaveBeenCalledWith(expect.any(AbortSignal)));
  await waitFor(() => expect(api.getTopologyGraph).toHaveBeenCalledWith("live", expect.any(AbortSignal)));
});

test("captures an ephemeral snapshot and runs a bounded live probe", async () => {
  healthyResponses();
  const monitoring = {
    observed_at: "2026-11-02T10:00:00Z", topology_name: "netrca_lab_v1", network_state: "RUNNING", collection_status: "COMPLETE", counter_unit: "bytes_and_packets", errors: [], links: [],
    devices: [
      { name: "h1", device_type: "HOST", interfaces: [{ name: "h1-eth0", status: "UP", rx_bytes: 10, tx_bytes: 20, rx_errors: 0, tx_errors: 0 }] },
      { name: "h2", device_type: "HOST", interfaces: [{ name: "h2-eth0", status: "UP", rx_bytes: 20, tx_bytes: 10, rx_errors: 0, tx_errors: 0 }] },
    ],
  };
  api.getMonitoring.mockResolvedValue({ data: monitoring });
  api.probeNetwork.mockResolvedValue({ data: { observed_at: "2026-11-02T10:01:00Z", source: "h1", destination: "h2", packets_sent: 2, packets_received: 2, packet_loss_percent: 0, latency_ms: 0.02, status: "REACHABLE" } });
  render(<Home />);
  expect(await screen.findByText("API connected")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Evidence" }));
  fireEvent.click(await screen.findByRole("button", { name: "Capture live snapshot" }));
  await waitFor(() => expect(api.getMonitoring).toHaveBeenCalledWith(expect.any(AbortSignal)));
  fireEvent.click(await screen.findByRole("button", { name: "Run bounded probe" }));
  await waitFor(() => expect(api.probeNetwork).toHaveBeenCalledWith("h1", "h2", expect.any(AbortSignal)));
  expect(await screen.findByText(/h1 → h2: REACHABLE/)).toBeInTheDocument();
});

test("injects a controlled fault using only targets from the live snapshot", async () => {
  healthyResponses();
  const monitoring = {
    observed_at: "2026-11-02T10:00:00Z", topology_name: "netrca_lab_v1", network_state: "RUNNING", collection_status: "COMPLETE", errors: [],
    devices: [{ name: "h1", device_type: "HOST", interfaces: [{ name: "h1-eth0", status: "UP", rx_errors: 0, tx_errors: 0 }] }],
    links: [{ source: "h1", destination: "s1", status: "UP" }],
  };
  api.getMonitoring.mockResolvedValue({ data: monitoring });
  api.injectFault.mockResolvedValue({ data: { id: "fault-1", status: "ACTIVE" } });
  render(<Home />);
  fireEvent.click(await screen.findByRole("button", { name: "Fault Lab" }));
  expect(await screen.findByText("Controlled fault and observable failure")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Fault type"), { target: { value: "PACKET_LOSS" } });
  fireEvent.click(screen.getByRole("button", { name: "Inject controlled fault" }));
  await waitFor(() => expect(api.injectFault).toHaveBeenCalledWith({
    fault_type: "PACKET_LOSS", device: "h1", interface: "h1-eth0", packet_loss_percent: 50,
    duration_seconds: 30, severity: "HIGH",
  }, expect.any(AbortSignal)));
});

test("stores an explicit snapshot and analyzes selected stored metrics without persistence", async () => {
  healthyResponses();
  const metric = { id: "metric-1", metric_type: "PACKET_LOSS", value: 100, unit: "%", timestamp: "2026-11-02T10:00:00Z", source: "mininet_probe" };
  api.getPage.mockImplementation(async (resource: string) => ({ data: resource === "metrics" ? [metric] : [], pagination: { page: 1, limit: 20, total: resource === "metrics" ? 1 : 0, pages: resource === "metrics" ? 1 : 0 } }));
  api.collectEvidenceSnapshot.mockResolvedValue({ data: { observed_at: "2026-11-02T10:01:00Z", metrics: 10, events: 1, duplicates: 0 } });
  api.detectStoredMetrics.mockResolvedValue({ data: { anomalies_detected: 1, insufficient_data: 0, persisted: 0, items: [{ metric_id: "metric-1", observation_key: "probe:key", metric_type: "PACKET_LOSS", value: 100, unit: "%", observed_at: "2026-11-02T10:00:00Z", status: "ANOMALY", method: "THRESHOLD", reason: "Packet loss exceeds the configured threshold", severity: "CRITICAL", score: 1, score_kind: "THRESHOLD_STRENGTH", support: {}, baseline_samples: 0, persistence: "NOT_REQUESTED" }] } });
  render(<Home />);
  fireEvent.click(await screen.findByRole("button", { name: "Detection Lab" }));
  fireEvent.click(await screen.findByRole("button", { name: "Store current snapshot" }));
  await waitFor(() => expect(api.collectEvidenceSnapshot).toHaveBeenCalledWith(expect.any(AbortSignal)));
  expect(await screen.findByText("Collection completed")).toBeInTheDocument();
  fireEvent.click(screen.getByLabelText("Select PACKET_LOSS metric metric-1"));
  fireEvent.click(screen.getByRole("button", { name: "Analyze selected metrics" }));
  await waitFor(() => expect(api.detectStoredMetrics).toHaveBeenCalledWith(["metric-1"], expect.any(AbortSignal)));
  expect(await screen.findByText("Packet loss exceeds the configured threshold")).toBeInTheDocument();
});

test("correlates only selected stored evidence and displays grounded reasons", async () => {
  healthyResponses();
  const event = { id: "event-1", event_type: "LINK_FAILURE", severity: "HIGH", timestamp: "2026-11-03T10:00:00Z", message: "Link down" };
  const anomaly = { id: "anomaly-1", name: "Packet loss", severity: "HIGH", detected_at: "2026-11-03T10:00:10Z", model_name: "NETRCA_THRESHOLD", is_anomaly: true };
  api.getPage.mockImplementation(async (resource: string) => ({ data: resource === "events" ? [event] : resource === "anomalies" ? [anomaly] : [], pagination: { page: 1, limit: 20, total: ["events", "anomalies"].includes(resource) ? 1 : 0, pages: ["events", "anomalies"].includes(resource) ? 1 : 0 } }));
  api.correlateEvidence.mockResolvedValue({ data: { created: 1, attached: 2, skipped_ids: [], incidents: [{ incident_id: "incident-1", created: true, evidence: [{ kind: "EVENT", id: "event-1", reason: "SEED" }, { kind: "ANOMALY", id: "anomaly-1", reason: "SAME_LINK" }] }] } });
  render(<Home />);
  fireEvent.click(await screen.findByRole("button", { name: "Correlation Lab" }));
  fireEvent.click(await screen.findByLabelText("Select event event-1"));
  fireEvent.click(screen.getByLabelText("Select anomaly anomaly-1"));
  fireEvent.click(screen.getByRole("button", { name: "Correlate selected evidence" }));
  await waitFor(() => expect(api.correlateEvidence).toHaveBeenCalledWith(["event-1"], ["anomaly-1"], expect.any(AbortSignal)));
  expect(await screen.findByText(/SAME LINK/i)).toBeInTheDocument();
});

test("runs deterministic RCA for the selected incident and exposes rule provenance", async () => {
  healthyResponses();
  const incident = { id: "incident-1", title: "Inter-switch outage", severity: "HIGH", status: "DETECTED", start_time: "2026-11-03T10:00:00Z" };
  const detail = { ...incident, description: "Stored evidence", events: [{ id: "event-1", event_type: "LINK_FAILURE" }], anomalies: [{ id: "anomaly-1", name: "Packet loss" }] };
  const rca = { id: "run-1", incident_id: incident.id, analysis_version: "RULES_V1", input_fingerprint: "hash", status: "CANDIDATES", created_at: incident.start_time, last_analyzed_at: incident.start_time, result: { incident_id: incident.id, status: "CANDIDATES", evidence_count: 2, analysis_version: "RULES_V1", limitations: [], candidates: [{ cause_type: "LINK_FAILURE", target_kind: "LINK", target_id: "link-1", score: 4, score_kind: "UNCALIBRATED_RULE_POINTS", explanation: "Direct failure evidence", contributions: [{ rule: "DIRECT_FAILURE", points: 4, evidence: [{ source_type: "EVENT", source_id: "event-1", reason: "DIRECT_FAILURE" }] }], supporting_evidence: [{ source_type: "EVENT", source_id: "event-1", reason: "DIRECT_FAILURE" }], contradictory_evidence: [], limitations: [] }] } };
  api.getPage.mockImplementation(async (resource: string) => ({ data: resource === "incidents" ? [incident] : [], pagination: { page: 1, limit: 20, total: resource === "incidents" ? 1 : 0, pages: resource === "incidents" ? 1 : 0 } }));
  api.getIncident.mockResolvedValue(detail);
  api.getIncidentRca.mockRejectedValue(new Error("No current RCA result"));
  api.getIncidentImpact.mockRejectedValue(new Error("No current impact result"));
  api.runIncidentRca.mockResolvedValue({ data: rca });
  render(<Home />);
  fireEvent.click(await screen.findByRole("button", { name: "RCA Lab" }));
  fireEvent.click(await screen.findByRole("button", { name: /Inter-switch outage/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Run deterministic RCA" }));
  await waitFor(() => expect(api.runIncidentRca).toHaveBeenCalledWith("incident-1", expect.any(AbortSignal)));
  expect(await screen.findByText("RANK 1")).toBeInTheDocument();
  expect(screen.getByText(/not probability or confidence/i)).toBeInTheDocument();
});

test("runs impact analysis for an incident with RCA and distinguishes observed from potential exposure", async () => {
  healthyResponses();
  const incident = { id: "incident-1", title: "Inter-switch outage", severity: "HIGH", status: "DETECTED", start_time: "2026-11-03T10:00:00Z" };
  const detail = { ...incident, events: [{ id: "event-1" }], anomalies: [{ id: "anomaly-1" }] };
  const rca = { id: "rca-1", incident_id: incident.id, analysis_version: "RULES_V1", input_fingerprint: "hash", status: "CANDIDATES", created_at: incident.start_time, last_analyzed_at: incident.start_time, result: { incident_id: incident.id, status: "CANDIDATES", evidence_count: 2, analysis_version: "RULES_V1", limitations: [], candidates: [] } };
  const impact = { id: "impact-1", rca_run_id: rca.id, analysis_version: "IMPACT_RULES_V1", input_fingerprint: "input", topology_fingerprint: "topology", status: "ASSESSED", created_at: incident.start_time, last_analyzed_at: incident.start_time, result: { incident_id: incident.id, rca_run_id: rca.id, status: "ASSESSED", candidate_target_kind: "LINK", candidate_target_id: "link-1", affected_devices: 1, affected_links: 1, affected_services: 0, user_application_impact: "UNKNOWN_UNVERIFIED", topology_input: {}, limitations: [], analysis_version: "IMPACT_RULES_V1", entities: [{ kind: "LINK", id: "link-1", classification: "OBSERVED", explanation: "Direct evidence", evidence: [{ source_type: "EVENT", source_id: "event-1", reason: "DIRECT_FAILURE" }] }, { kind: "DEVICE", id: "device-1", classification: "POTENTIAL", explanation: "Endpoint exposure", evidence: [{ source_type: "EVENT", source_id: "event-1", reason: "DIRECT_FAILURE" }] }], chain: [{ step: 1, source_kind: "LINK", source_id: "link-1", target_kind: "DEVICE", target_id: "device-1", relationship: "LINK_ENDPOINT", classification: "POTENTIAL", explanation: "Physical endpoint", evidence: [{ source_type: "EVENT", source_id: "event-1", reason: "DIRECT_FAILURE" }] }] } };
  api.getPage.mockImplementation(async (resource: string) => ({ data: resource === "incidents" ? [incident] : [], pagination: { page: 1, limit: 20, total: resource === "incidents" ? 1 : 0, pages: resource === "incidents" ? 1 : 0 } }));
  api.getIncident.mockResolvedValue(detail);
  api.getIncidentRca.mockResolvedValue({ data: rca });
  api.getIncidentImpact.mockRejectedValue(new Error("No current impact result"));
  api.runIncidentImpact.mockResolvedValue({ data: impact });
  render(<Home />);
  fireEvent.click(await screen.findByRole("button", { name: "Impact Lab" }));
  fireEvent.click(await screen.findByRole("button", { name: /Inter-switch outage/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Run impact analysis" }));
  await waitFor(() => expect(api.runIncidentImpact).toHaveBeenCalledWith("incident-1", expect.any(AbortSignal)));
  expect(await screen.findByText("OBSERVED")).toBeInTheDocument();
  expect(screen.getAllByText("POTENTIAL").length).toBeGreaterThan(0);
  expect(screen.getByText(/not confirmed failure/i)).toBeInTheDocument();
});

test("surfaces backend failures without replacing them with demonstration data", async () => {
  healthyResponses();
  api.getPage.mockImplementation(async (resource: string) => {
    if (resource === "incidents") throw new Error("The database is unavailable. Check the backend database configuration.");
    return { data: [], pagination: { page: 1, limit: 20, total: 0, pages: 0 } };
  });
  render(<Home />);
  fireEvent.click(within(screen.getByRole("navigation", { name: "Workspace" })).getByRole("button", { name: "Incidents" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("database is unavailable");
});

test("loads incident evidence and distinguishes candidate scores from probabilities", async () => {
  healthyResponses();
  const incident = { id: "incident-1", title: "Interface degradation", severity: "HIGH", status: "INVESTIGATING", start_time: "2026-10-15T10:00:00Z" };
  api.getPage.mockImplementation(async (resource: string) => ({ data: resource === "incidents" ? [incident] : [], pagination: { page: 1, limit: 20, total: resource === "incidents" ? 1 : 0, pages: resource === "incidents" ? 1 : 0 } }));
  api.getIncident.mockResolvedValue({ ...incident, events: [{ id: "event-1", event_type: "INTERFACE_FAILURE", message: "Interface changed to DOWN", severity: "HIGH", timestamp: incident.start_time }], anomalies: [] });
  api.getIncidentRca.mockResolvedValue({ data: { result: { status: "CANDIDATES", candidates: [{ cause_type: "INTERFACE_FAILURE", score: 42, explanation: "Evidence supports an interface fault", supporting_evidence: [{}], contradictory_evidence: [] }] } } });
  api.getIncidentImpact.mockRejectedValue(new Error("No current impact result"));
  api.generateIncidentExplanation.mockResolvedValue({ data: { summary: [{ claim_id: "C001", text: "An interface failure preceded the event.", evidence_references: [{ source_type: "EVENT", source_id: "event-1" }] }] } });
  render(<Home />);
  fireEvent.click(await screen.findByRole("button", { name: /Interface degradation/ }));
  expect(await screen.findByText("Evidence supports an interface fault")).toBeInTheDocument();
  expect(screen.getByText(/uncalibrated points, not probability/)).toBeInTheDocument();
  expect(screen.getByText("Impact and failure chain")).toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent("No current impact result");
  fireEvent.click(screen.getByRole("button", { name: "Generate explanation" }));
  expect(await screen.findByText("An interface failure preceded the event.")).toBeInTheDocument();
  expect(api.generateIncidentExplanation).toHaveBeenCalledWith("incident-1");
  await waitFor(() => expect(api.getIncident).toHaveBeenCalledWith("incident-1", expect.any(AbortSignal)));
});

test("keeps an RCA retrieval failure distinct from an absent RCA result", async () => {
  healthyResponses();
  const incident = { id: "incident-2", title: "Unavailable RCA", severity: "MEDIUM", status: "DETECTED", start_time: "2026-10-15T10:00:00Z" };
  api.getPage.mockImplementation(async (resource: string) => ({ data: resource === "incidents" ? [incident] : [], pagination: { page: 1, limit: 20, total: resource === "incidents" ? 1 : 0, pages: resource === "incidents" ? 1 : 0 } }));
  api.getIncident.mockResolvedValue({ ...incident, events: [], anomalies: [] });
  api.getIncidentRca.mockRejectedValue(new Error("The database is unavailable."));
  api.getIncidentImpact.mockResolvedValue({ data: {} });
  render(<Home />);
  fireEvent.click(screen.getByRole("button", { name: "Incidents" }));
  fireEvent.click(await screen.findByRole("button", { name: /Unavailable RCA/ }));
  expect(await screen.findByRole("alert")).toHaveTextContent("database is unavailable");
  expect(screen.queryByText("No current RCA result is available. Run analysis if enabled on the backend.")).not.toBeInTheDocument();
});

test("switches graph source without retaining a selection from the previous source", async () => {
  healthyResponses();
  api.getTopologyGraph.mockImplementation(async (source: string) => ({ data: {
    directed: false, semantics: "PHYSICAL_TOPOLOGY", connected: true, components: [[source === "live" ? "live-id" : "stored-id"]],
    devices: [{ id: source === "live" ? "live-id" : "stored-id", name: "edge-host", device_type: "HOST", status: source === "live" ? "PRESENT" : "HEALTHY" }], links: [],
  } }));
  render(<Home />);
  fireEvent.click(screen.getByRole("button", { name: "Topology" }));
  expect(await screen.findByRole("button", { name: /Device edge-host/ })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Device edge-host/ }));
  expect(screen.getByRole("heading", { name: "edge-host" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Stored topology" }));
  expect(await screen.findByRole("button", { name: /Device edge-host/ })).toBeInTheDocument();
  expect(screen.getByText(/Select a device or link/)).toBeInTheDocument();
  expect(screen.queryByText("live-id")).not.toBeInTheDocument();
  expect(api.getTopologyGraph).toHaveBeenCalledWith("stored", expect.any(AbortSignal));
});

test("opens stored topology from incident evidence context without running analysis", async () => {
  healthyResponses();
  const incident = { id: "incident-1", title: "Stored incident", severity: "MEDIUM", status: "DETECTED", start_time: "2026-10-15T10:00:00Z" };
  api.getPage.mockImplementation(async (resource: string) => ({ data: resource === "incidents" ? [incident] : [], pagination: { page: 1, limit: 20, total: resource === "incidents" ? 1 : 0, pages: resource === "incidents" ? 1 : 0 } }));
  api.getIncident.mockResolvedValue({ ...incident, events: [], anomalies: [] });
  api.getIncidentRca.mockResolvedValue({ data: {} });
  api.getIncidentImpact.mockResolvedValue({ data: {} });
  api.getIncidentTopologyContext.mockResolvedValue({ data: {
    incident_id: incident.id, source: "stored", evidence: [], referenced_device_ids: ["stored-device"], referenced_link_ids: [],
    context_device_ids: ["stored-device"], context_link_ids: [], missing_device_ids: [], missing_link_ids: [], unmapped_service_ids: [],
  } });
  render(<Home />);
  fireEvent.click(screen.getByRole("button", { name: "Incidents" }));
  fireEvent.click(await screen.findByRole("button", { name: /Stored incident/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Show evidence in stored topology" }));
  expect(await screen.findByText(/Showing stored graph context for/)).toBeInTheDocument();
  expect(api.getIncidentTopologyContext).toHaveBeenCalledWith("incident-1", expect.any(AbortSignal));
  expect(api.runIncidentRca).not.toHaveBeenCalled();
  expect(api.runIncidentImpact).not.toHaveBeenCalled();
});
