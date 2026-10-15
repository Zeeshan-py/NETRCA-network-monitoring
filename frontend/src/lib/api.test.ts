import { afterEach, expect, test, vi } from "vitest";
import { ApiError, apiRequest, getPage, getTopology } from "./api";

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
