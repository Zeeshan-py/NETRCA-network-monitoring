import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { TopologyEvidence } from "./topology-evidence";

const api = vi.hoisted(() => ({ getPage: vi.fn() }));
vi.mock("@/lib/api", () => api);
afterEach(() => { cleanup(); vi.clearAllMocks(); });

test("loads only supported device-filtered evidence and preserves pagination", async () => {
  api.getPage.mockImplementation(async (resource: string, page: number) => ({
    data: [{ id: `${resource}-${page}`, timestamp: "2026-10-15T12:00:00Z", message: "Observed record", event_type: resource.toUpperCase() }],
    pagination: { page, limit: 20, total: 21, pages: 2 },
  }));
  render(<TopologyEvidence selection={{ kind: "device", id: "stored-device" }} label="router-a" onBack={vi.fn()} onBrowseIncidents={vi.fn()} />);
  expect((await screen.findAllByText("Observed record")).length).toBeGreaterThan(0);
  await waitFor(() => expect(api.getPage).toHaveBeenCalledTimes(4));
  expect(api.getPage).toHaveBeenCalledWith("metrics", 1, 20, expect.any(AbortSignal), { deviceId: "stored-device" });
  expect(api.getPage).toHaveBeenCalledWith("anomalies", 1, 20, expect.any(AbortSignal), { deviceId: "stored-device" });
  fireEvent.click(screen.getAllByRole("button", { name: "Next" })[0]);
  expect(await screen.findByText("Evidence ID: metrics-2")).toBeInTheDocument();
  expect(api.getPage).toHaveBeenCalledWith("metrics", 2, 20, expect.any(AbortSignal), { deviceId: "stored-device" });
});

test("uses link filters only on metrics and events and reports failures safely", async () => {
  api.getPage.mockImplementation(async (resource: string) => {
    if (resource === "events") throw new Error("Evidence storage unavailable");
    return { data: [], pagination: { page: 1, limit: 20, total: 0, pages: 0 } };
  });
  render(<TopologyEvidence selection={{ kind: "link", id: "stored-link" }} label="router-a ↔ switch-b" onBack={vi.fn()} onBrowseIncidents={vi.fn()} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Evidence storage unavailable");
  expect(api.getPage).toHaveBeenCalledTimes(2);
  expect(api.getPage).toHaveBeenCalledWith("metrics", 1, 20, expect.any(AbortSignal), { linkId: "stored-link" });
  expect(api.getPage).toHaveBeenCalledWith("events", 1, 20, expect.any(AbortSignal), { linkId: "stored-link" });
  expect(screen.getByText(/No incident association is inferred/)).toBeInTheDocument();
});
