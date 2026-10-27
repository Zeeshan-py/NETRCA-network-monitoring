import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import Home from "./page";

const api = vi.hoisted(() => ({
  getApiHealth: vi.fn(), getNetworkStatus: vi.fn(), getTopology: vi.fn(), getMonitoring: vi.fn(),
  getPage: vi.fn(), getIncident: vi.fn(), getIncidentRca: vi.fn(), getIncidentImpact: vi.fn(),
  getTopologyGraph: vi.fn(), getIncidentTopologyContext: vi.fn(),
  runIncidentRca: vi.fn(), runIncidentImpact: vi.fn(), correlateEvidence: vi.fn(), generateIncidentExplanation: vi.fn(),
}));
vi.mock("@/lib/api", () => api);

afterEach(() => { cleanup(); vi.clearAllMocks(); });

function healthyResponses() {
  api.getApiHealth.mockResolvedValue({ data: { api: "UP" } });
  api.getNetworkStatus.mockResolvedValue({ data: { state: "RUNNING", topology_name: "lab", device_count: 2, link_count: 1 } });
  api.getTopology.mockResolvedValue({ data: { nodes: [{ id: "d1", name: "h1", device_type: "HOST", state: "PRESENT" }], links: [] } });
  api.getMonitoring.mockResolvedValue({ data: { observed_at: "2026-10-15T10:00:00Z", network_state: "RUNNING", collection_status: "COMPLETE", devices: [], links: [], errors: [] } });
  api.getTopologyGraph.mockResolvedValue({ data: { directed: false, semantics: "PHYSICAL_TOPOLOGY", connected: true, components: [["d1"]], devices: [{ id: "d1", name: "h1", device_type: "HOST", status: "PRESENT" }], links: [] } });
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
