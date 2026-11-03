import { afterEach, expect, test, vi } from "vitest";
import { ApiError, apiRequest, collectEvidenceProbe, collectEvidenceSnapshot, correlateEvidence, detectStoredMetrics, getFaults, getIncidentTopologyContext, getPage, getTopology, getTopologyGraph, injectFault, probeNetwork, recoverFault, resetFaults, resetNetwork, runIncidentRca, startNetwork, stopNetwork, testNetworkConnectivity } from "./api";

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

test("uses the configured API base and disables browser caching", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1/");
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: { api: "UP" } }) });
  vi.stubGlobal("fetch", fetchMock);
  await apiRequest("/health");
  expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/v1/health", expect.objectContaining({ cache: "no-store", method: "GET" }));
});

test("normalizes both supported paginated API response envelopes", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ success: true, data: [{ id: "a" }], pagination: { page: 1, limit: 20, total: 1, pages: 1 } }) })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ success: true, data: { data: [{ id: "b" }], pagination: { page: 1, limit: 20, total: 1, pages: 1 } } }) });
  vi.stubGlobal("fetch", fetchMock);
  expect(await getPage("anomalies")).toMatchObject({ data: [{ id: "a" }], pagination: { total: 1 } });
  expect(await getPage("incidents")).toMatchObject({ data: [{ id: "b" }], pagination: { total: 1 } });
});

test("falls back to stored topology only when the simulator is disabled", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({ success: false, error: { code: "MININET_UNAVAILABLE", message: "SIMULATION_DISABLED" } }) })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ success: true, data: { nodes: [{ id: "device-id", name: "switch-a", device_type: "SWITCH", status: "HEALTHY" }], links: [], components: [["device-id"]] } }) });
  vi.stubGlobal("fetch", fetchMock);
  await expect(getTopology()).resolves.toMatchObject({ data: { nodes: [{ name: "switch-a" }] } });
  expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["http://localhost:8000/api/v1/topology", "http://localhost:8000/api/v1/topology?source=stored"]);
});

test("surfaces sanitized API validation and access-control errors", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 403, json: async () => ({ success: false, error: { code: "RCA_WRITES_DISABLED", message: "RCA runs are disabled by the backend configuration." } }) }));
  await expect(apiRequest("/incidents/id/root-cause/analyze", { method: "POST", localControl: true })).rejects.toMatchObject({ status: 403, code: "RCA_WRITES_DISABLED", message: "RCA runs are disabled by the backend configuration." });
});

test("surfaces validation failures and does not add local-control headers to ordinary requests", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 422, json: async () => ({ success: false, error: { code: "VALIDATION_ERROR", message: "Request validation failed" } }) });
  vi.stubGlobal("fetch", fetchMock);
  await expect(apiRequest("/events/correlate", { method: "POST", body: { event_ids: [] } })).rejects.toMatchObject({ status: 422, code: "VALIDATION_ERROR" });
  expect(new Headers(fetchMock.mock.calls[0][1].headers).has("X-NetRCA-Local-Control")).toBe(false);
});

test("requires a valid URL and turns network failures into actionable errors", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://user:pass@example.test/api");
  await expect(apiRequest("/health")).rejects.toBeInstanceOf(ApiError);
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connection refused")));
  await expect(apiRequest("/health")).rejects.toMatchObject({ message: expect.stringContaining("Check that the backend is running") });
});

test("adds the established local-control header only to explicit protected actions", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: {} }) });
  vi.stubGlobal("fetch", fetchMock);
  await apiRequest("/events/correlate", { method: "POST", localControl: true, body: { event_ids: ["event"], anomaly_ids: [] } });
  const request = fetchMock.mock.calls[0][1] as RequestInit;
  expect(new Headers(request.headers).get("X-NetRCA-Local-Control")).toBe("1");
  expect(request.body).toBe(JSON.stringify({ event_ids: ["event"], anomaly_ids: [] }));
});

test("uses protected POST requests for the fixed Mininet lifecycle", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: {} }) });
  vi.stubGlobal("fetch", fetchMock);
  await startNetwork();
  await testNetworkConnectivity();
  await resetNetwork();
  await stopNetwork();
  expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
    "http://localhost:8000/api/v1/network/start",
    "http://localhost:8000/api/v1/network/connectivity-test",
    "http://localhost:8000/api/v1/network/reset",
    "http://localhost:8000/api/v1/network/stop",
  ]);
  for (const [, request] of fetchMock.mock.calls) {
    expect(request.method).toBe("POST");
    expect(new Headers(request.headers).get("X-NetRCA-Local-Control")).toBe("1");
  }
});

test("preserves a completed disconnected-host measurement returned with 503", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: false,
    status: 503,
    json: async () => ({ success: true, data: { connected: false, hosts: ["h1", "h2", "server1"], packet_loss_percent: 50 } }),
  }));
  await expect(testNetworkConnectivity()).resolves.toMatchObject({ data: { connected: false, packet_loss_percent: 50 } });
});

test("runs only the bounded local monitoring probe contract", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: { status: "REACHABLE" } }) });
  vi.stubGlobal("fetch", fetchMock);
  await probeNetwork("h1", "server1");
  const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
  expect(url).toBe("http://localhost:8000/api/v1/network/monitoring/probe");
  expect(request.method).toBe("POST");
  expect(new Headers(request.headers).get("X-NetRCA-Local-Control")).toBe("1");
  expect(JSON.parse(String(request.body))).toEqual({ source: "h1", destination: "server1", count: 2, timeout_seconds: 2 });
});

test("uses protected bounded fault lifecycle requests", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  const pagination = { page: 1, limit: 100, total: 0, pages: 0 };
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ success: true, data: [], pagination }) })
    .mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: {} }) });
  vi.stubGlobal("fetch", fetchMock);
  await getFaults();
  await injectFault({ fault_type: "PACKET_LOSS", device: "h1", interface: "h1-eth0", packet_loss_percent: 50, duration_seconds: 30, severity: "HIGH" });
  await recoverFault("fault-id");
  await resetFaults();
  expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
    "http://localhost:8000/api/v1/faults?page=1&limit=100",
    "http://localhost:8000/api/v1/faults/inject",
    "http://localhost:8000/api/v1/faults/fault-id/recover",
    "http://localhost:8000/api/v1/faults/reset",
  ]);
  expect(new Headers(fetchMock.mock.calls[0][1].headers).has("X-NetRCA-Local-Control")).toBe(false);
  for (const [, request] of fetchMock.mock.calls.slice(1)) {
    expect(request.method).toBe("POST");
    expect(new Headers(request.headers).get("X-NetRCA-Local-Control")).toBe("1");
  }
  expect(JSON.parse(String(fetchMock.mock.calls[1][1].body))).toEqual({
    fault_type: "PACKET_LOSS", device: "h1", interface: "h1-eth0", packet_loss_percent: 50,
    duration_seconds: 30, severity: "HIGH",
  });
});

test("uses explicit protected evidence collection and non-persisting detection requests", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: {} }) });
  vi.stubGlobal("fetch", fetchMock);
  await collectEvidenceSnapshot();
  await collectEvidenceProbe("h1", "server1");
  await detectStoredMetrics(["metric-1", "metric-2"]);
  expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
    "http://localhost:8000/api/v1/pipeline/collect",
    "http://localhost:8000/api/v1/pipeline/probe",
    "http://localhost:8000/api/v1/anomalies/detect",
  ]);
  for (const [, request] of fetchMock.mock.calls) {
    expect(request.method).toBe("POST");
    expect(new Headers(request.headers).get("X-NetRCA-Local-Control")).toBe("1");
  }
  expect(JSON.parse(String(fetchMock.mock.calls[1][1].body))).toEqual({ source: "h1", destination: "server1", count: 2, timeout_seconds: 2 });
  expect(JSON.parse(String(fetchMock.mock.calls[2][1].body))).toEqual({ metric_ids: ["metric-1", "metric-2"], persist: false });
});

test("submits only explicitly selected evidence to protected correlation", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: { incidents: [], skipped_ids: [], created: 0, attached: 0 } }) });
  vi.stubGlobal("fetch", fetchMock);
  await correlateEvidence(["event-1"], ["anomaly-1"]);
  const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
  expect(url).toBe("http://localhost:8000/api/v1/events/correlate");
  expect(request.method).toBe("POST");
  expect(new Headers(request.headers).get("X-NetRCA-Local-Control")).toBe("1");
  expect(JSON.parse(String(request.body))).toEqual({ event_ids: ["event-1"], anomaly_ids: ["anomaly-1"] });
});

test("runs deterministic RCA only through the protected incident action", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: {} }) });
  vi.stubGlobal("fetch", fetchMock);
  await runIncidentRca("incident/unsafe");
  const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
  expect(url).toBe("http://localhost:8000/api/v1/incidents/incident%2Funsafe/root-cause/analyze");
  expect(request.method).toBe("POST");
  expect(new Headers(request.headers).get("X-NetRCA-Local-Control")).toBe("1");
  expect(request.body).toBeUndefined();
});

test("requests live and stored graph sources separately without mixing them", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  const graph = { directed: false, semantics: "PHYSICAL_TOPOLOGY", connected: true, components: [["live-id"]], devices: [{ id: "live-id", name: "h1", device_type: "HOST", status: "PRESENT" }], links: [] };
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: graph }) });
  vi.stubGlobal("fetch", fetchMock);
  await getTopologyGraph("live");
  await getTopologyGraph("stored");
  expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
    "http://localhost:8000/api/v1/topology/analysis?source=live",
    "http://localhost:8000/api/v1/topology/analysis?source=stored",
  ]);
  expect(new Headers(fetchMock.mock.calls[0][1].headers).has("X-NetRCA-Local-Control")).toBe(false);
});

test("rejects malformed graph contracts while preserving absent status as unknown data", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  const malformed = { directed: false, semantics: "PHYSICAL_TOPOLOGY", connected: true, components: [], devices: [{ id: "d", name: "host", device_type: "HOST" }], links: "bad" };
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: malformed }) }));
  await expect(getTopologyGraph("stored")).rejects.toMatchObject({ message: expect.stringContaining("graph contract") });
});

test("uses only supported stored filters for evidence queries", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  const page = { data: [], pagination: { page: 1, limit: 20, total: 0, pages: 0 } };
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, ...page }) });
  vi.stubGlobal("fetch", fetchMock);
  await getPage("metrics", 1, 20, undefined, { deviceId: "device-uuid" });
  await getPage("events", 1, 20, undefined, { linkId: "link-uuid" });
  await getPage("anomalies", 1, 20, undefined, { linkId: "unsupported-link-filter" });
  expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
    "http://localhost:8000/api/v1/metrics?page=1&limit=20&device_id=device-uuid",
    "http://localhost:8000/api/v1/events?page=1&limit=20&link_id=link-uuid",
    "http://localhost:8000/api/v1/anomalies?page=1&limit=20",
  ]);
});

test("validates incident topology context as a stored relationship", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  const context = { incident_id: "incident-1", source: "stored", evidence: [], referenced_device_ids: [], referenced_link_ids: [], context_device_ids: ["device-1"], context_link_ids: [], missing_device_ids: [], missing_link_ids: [], unmapped_service_ids: [] };
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: context }) });
  vi.stubGlobal("fetch", fetchMock);
  await getIncidentTopologyContext("incident-1");
  expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/api/v1/incidents/incident-1/topology-context");
  expect(new Headers(fetchMock.mock.calls[0][1].headers).has("X-NetRCA-Local-Control")).toBe(false);
});

test("rejects incident topology context returned for a different incident", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  const context = { incident_id: "other-incident", source: "stored", evidence: [], referenced_device_ids: [], referenced_link_ids: [], context_device_ids: [], context_link_ids: [], missing_device_ids: [], missing_link_ids: [], unmapped_service_ids: [] };
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: context }) }));
  await expect(getIncidentTopologyContext("incident-1")).rejects.toMatchObject({ message: expect.stringContaining("context response") });
});
